"""Pin forwarder hosts to the IPs the subscription's own DNS gives them.

An airport's entry host can exist only on the private resolver named in its
Clash ``dns.nameserver-policy`` (a DoH endpoint), which glider's DNS client
cannot query. So the A record is resolved here and written into the main config
as a glider ``dnsrecord=`` line; glider's rule files do not accept that option.
"""

import base64
import ipaddress
import secrets
import socket
import struct
from typing import Any, Callable, Dict, List, Sequence, Tuple, Union
from urllib.parse import urlparse

import requests

from medusa.utils.logging import get_logger

logger = get_logger(__name__)

QTYPE_A = 1
QCLASS_IN = 1
RCODES = {1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}

Server = Tuple[str, Union[str, Tuple[str, int]]]
Policy = Tuple[str, List[str]]


def parse_server(server: str) -> Server:
    """Classify a nameserver-policy server as ("doh", url) or ("udp", (host, port)).

    Accepts ``host/path`` and ``https://host/path`` (DoH) and ``ip[:port]`` (UDP).
    """
    # mihomo appends per-server options after '#', e.g. "...#PROXY&h3=true".
    s = server.strip().split("#", 1)[0]
    if s.startswith(("https://", "http://")):
        return "doh", s
    if s.startswith("udp://"):
        s = s[len("udp://") :]
    elif "://" in s:
        raise ValueError(f"unsupported DNS server scheme: {server}")
    if "/" in s:
        return "doh", f"https://{s}"
    parsed = urlparse(f"//{s}")
    if not parsed.hostname:
        raise ValueError(f"unparseable DNS server: {server}")
    return "udp", (parsed.hostname, parsed.port or 53)


def build_query(host: str, qid: int) -> bytes:
    """DNS wire-format query for the A record of ``host`` (recursion desired)."""
    qname = b"".join(
        bytes([len(label)]) + label
        for label in (part.encode("idna") for part in host.rstrip(".").split("."))
    )
    header = struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    return header + qname + b"\x00" + struct.pack("!HH", QTYPE_A, QCLASS_IN)


def _skip_name(msg: bytes, off: int) -> int:
    while True:
        length = msg[off]
        if length & 0xC0 == 0xC0:
            return off + 2
        off += length + 1
        if length == 0:
            return off


def parse_a_records(msg: bytes, qid: int) -> List[str]:
    """IPv4 addresses in the answer section; raises LookupError on an empty result."""
    rid, flags, qdcount, ancount, _, _ = struct.unpack_from("!HHHHHH", msg)
    if rid != qid:
        raise ValueError(f"DNS response id {rid} does not match query id {qid}")
    rcode = flags & 0x000F
    if rcode:
        raise LookupError(RCODES.get(rcode, f"rcode {rcode}"))
    off = 12
    for _ in range(qdcount):
        off = _skip_name(msg, off) + 4
    ips = []
    for _ in range(ancount):
        off = _skip_name(msg, off)
        rtype, rclass, _ttl, rdlength = struct.unpack_from("!HHIH", msg, off)
        off += 10
        if rtype == QTYPE_A and rclass == QCLASS_IN and rdlength == 4:
            ips.append(socket.inet_ntoa(msg[off : off + 4]))
        off += rdlength
    if not ips:
        raise LookupError("no A record in answer")
    return ips


def _exchange_doh(url: str, query: bytes, timeout: float) -> bytes:
    # RFC 8484 GET.
    encoded = base64.urlsafe_b64encode(query).rstrip(b"=").decode()
    response = requests.get(
        url,
        params={"dns": encoded},
        headers={"Accept": "application/dns-message"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.content


def _exchange_udp(addr: Tuple[str, int], query: bytes, timeout: float) -> bytes:
    family, socktype, proto, _, sockaddr = socket.getaddrinfo(
        addr[0], addr[1], type=socket.SOCK_DGRAM
    )[0]
    with socket.socket(family, socktype, proto) as sock:
        sock.settimeout(timeout)
        sock.connect(sockaddr)
        sock.send(query)
        return sock.recv(4096)


def resolve_a(
    server: str, host: str, timeout: float = 5.0, attempts: int = 2
) -> List[str]:
    """Resolve ``host`` through one nameserver-policy server.

    Transport failures are retried; a definitive answer (NXDOMAIN, no A) is not.
    """
    kind, target = parse_server(server)
    # RFC 8484 asks DoH clients for id 0 so GET responses stay cacheable.
    qid = 0 if kind == "doh" else secrets.randbelow(0x10000)
    query = build_query(host, qid)
    for attempt in range(attempts):
        try:
            if kind == "doh":
                response = _exchange_doh(target, query, timeout)
            else:
                response = _exchange_udp(target, query, timeout)
            break
        except OSError:  # requests.RequestException and socket.timeout included
            if attempt == attempts - 1:
                raise
    return parse_a_records(response, qid)


def extract_policies(clash_configs: Sequence[Dict[str, Any]]) -> List[Policy]:
    """(domain pattern, [server, ...]) pairs from each config's nameserver-policy."""
    policies: List[Policy] = []
    for config in clash_configs:
        dns = config.get("dns") if isinstance(config, dict) else None
        policy = dns.get("nameserver-policy") if isinstance(dns, dict) else None
        if not isinstance(policy, dict):
            continue
        for key, value in policy.items():
            servers = value if isinstance(value, list) else [value]
            servers = [str(s) for s in servers if s]
            if not servers:
                continue
            for pattern in str(key).split(","):
                pattern = pattern.strip().lower()
                # geosite:/rule-set: keys name sets we cannot expand here.
                if pattern and ":" not in pattern:
                    policies.append((pattern, servers))
    return policies


def covers(pattern: str, host: str) -> bool:
    """Whether a nameserver-policy domain pattern applies to ``host``.

    Clash forms: ``+.d`` is d and all subdomains, ``.d`` subdomains only, and
    ``*`` stands for exactly one label. A bare ``d`` also covers its subdomains,
    as the generated rule file's ``domain=d`` does (Clash would match d alone).
    """
    host = host.lower().rstrip(".")
    if pattern.startswith("+."):
        base = pattern[2:]
        return host == base or host.endswith("." + base)
    if pattern.startswith("."):
        return host.endswith(pattern)
    if "*" in pattern:
        want, have = pattern.split("."), host.split(".")
        return len(want) == len(have) and all(w in ("*", h) for w, h in zip(want, have))
    return host == pattern or host.endswith("." + pattern)


def forward_hosts(forwards: Sequence[str]) -> List[str]:
    """Distinct non-IP hostnames of glider ``forward=`` lines, sorted."""
    hosts = set()
    for line in forwards:
        url = line.split("=", 1)[1] if line.startswith("forward=") else line
        hostname = urlparse(url.split(",", 1)[0]).hostname
        if not hostname:
            continue
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            hosts.add(hostname)
    return sorted(hosts)


def pin_forwarder_hosts(
    forwards: Sequence[str],
    clash_configs: Sequence[Dict[str, Any]],
    resolve: Callable[[str, str], List[str]] = resolve_a,
) -> List[str]:
    """``dnsrecord=<host>/<ip>`` lines for forwarder hosts a nameserver-policy covers.

    A host that fails to resolve is logged and left out; this never raises.
    """
    policies = extract_policies(clash_configs)
    if not policies:
        return []

    records: List[str] = []
    failed: List[str] = []
    for host in forward_hosts(forwards):
        servers = next((s for pattern, s in policies if covers(pattern, host)), None)
        if servers is None:
            continue
        errors = []
        for server in servers:
            try:
                ips = resolve(server, host)
                break
            except Exception as e:
                errors.append(f"{server}: {type(e).__name__}: {e}")
        else:
            logger.warning(f"Not pinning {host}: {'; '.join(errors)}")
            failed.append(host)
            continue
        if len(ips) > 1:
            logger.info(f"{host} has {len(ips)} A records, pinning the first: {ips}")
        records.append(f"dnsrecord={host}/{ips[0]}")

    summary = (
        f"Pinned {len(records)} forwarder host(s) via nameserver-policy DNS, "
        f"{len(failed)} failed"
    )
    if failed:
        logger.warning(f"{summary}: {', '.join(failed)}")
    else:
        logger.info(summary)
    return records
