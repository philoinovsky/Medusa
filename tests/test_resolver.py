"""Tests for pinning forwarder hosts via nameserver-policy DNS. No test uses the network."""

import base64
import logging
import socket
import struct
import threading
from pathlib import Path

import pytest
import requests

from medusa.cli.commands import GenerateCommand
from medusa.core import resolver
from medusa.core.resolver import (
    build_query,
    covers,
    extract_policies,
    forward_hosts,
    parse_a_records,
    parse_server,
    pin_forwarder_hosts,
    resolve_a,
)

TEMPLATE = (
    Path(__file__).parent.parent / "medusa" / "templates" / "glider_template.conf"
)
DOH = "https://doh.example.org/dns-query"


def query_host(query: bytes) -> str:
    labels, off = [], 12
    while query[off]:
        labels.append(query[off + 1 : off + 1 + query[off]].decode())
        off += query[off] + 1
    return ".".join(labels)


def make_response(query: bytes, ips=(), rcode=0, cname=None, qid=None) -> bytes:
    """Answer ``query`` the way a recursive resolver would, with name compression."""
    question = query[12:]
    answers, count, owner = b"", 0, b"\xc0\x0c"
    if cname:
        rdata = b"".join(bytes([len(p)]) + p.encode() for p in cname.split(".")) + b"\0"
        answers += owner + struct.pack("!HHIH", 5, 1, 60, len(rdata)) + rdata
        count += 1
        owner = struct.pack("!H", 0xC000 | (12 + len(question) + 12))
    for ip in ips:
        answers += owner + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton(ip)
        count += 1
    rid = struct.unpack_from("!H", query)[0] if qid is None else qid
    header = struct.pack("!HHHHHH", rid, 0x8180 | rcode, 1, count, 0, 0)
    return header + question + answers


class FakeDoH:
    """Stands in for requests.get against a DoH server with a fixed zone."""

    def __init__(self, zone):
        self.zone = zone
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        query = base64.urlsafe_b64decode(
            params["dns"] + "=" * (-len(params["dns"]) % 4)
        )
        host = query_host(query)
        self.calls.append((url, host, headers, query))
        ips = self.zone.get(host)
        response = requests.Response()
        response.status_code = 200
        response._content = make_response(query, ips or (), rcode=0 if ips else 3)
        return response


class TestParseServer:
    def test_doh_forms(self):
        assert parse_server("doh.example.org/dns-query") == ("doh", DOH)
        assert parse_server(DOH) == ("doh", DOH)
        assert parse_server(DOH + "#PROXY&h3=true") == ("doh", DOH)

    def test_udp_forms(self):
        assert parse_server("10.0.0.1:5353") == ("udp", ("10.0.0.1", 5353))
        assert parse_server("10.0.0.1") == ("udp", ("10.0.0.1", 53))
        assert parse_server("udp://10.0.0.1:53") == ("udp", ("10.0.0.1", 53))

    def test_unsupported_scheme(self):
        with pytest.raises(ValueError, match="unsupported"):
            parse_server("tls://dns.example.org")


class TestCovers:
    @pytest.mark.parametrize(
        "pattern, host, expected",
        [
            ("*.example.net", "entry.example.net", True),
            ("*.example.net", "example.net", False),
            ("*.example.net", "a.entry.example.net", False),
            ("+.example.net", "example.net", True),
            ("+.example.net", "a.entry.example.net", True),
            (".example.net", "entry.example.net", True),
            (".example.net", "example.net", False),
            ("example.net", "example.net", True),
            ("example.net", "entry.example.net", True),
            ("example.net", "notexample.net", False),
            ("a.*.example.net", "a.b.example.net", True),
            ("a.*.example.net", "c.b.example.net", False),
        ],
    )
    def test_patterns(self, pattern, host, expected):
        assert covers(pattern, host) is expected


class TestExtractPolicies:
    def test_shapes(self):
        configs = [
            {
                "dns": {
                    "nameserver-policy": {
                        "*.example.net": DOH,
                        "a.org, +.b.org": ["10.0.0.1", "10.0.0.2:53"],
                        "geosite:cn": "10.0.0.3",
                        "empty.org": [],
                    }
                }
            },
            {"dns": None},
            {"proxies": []},
        ]
        assert extract_policies(configs) == [
            ("*.example.net", [DOH]),
            ("a.org", ["10.0.0.1", "10.0.0.2:53"]),
            ("+.b.org", ["10.0.0.1", "10.0.0.2:53"]),
        ]


class TestWireFormat:
    def test_query_encodes_host(self):
        query = build_query("entry.example.net", 0x1234)
        assert struct.unpack_from("!HH", query) == (0x1234, 0x0100)
        assert query_host(query) == "entry.example.net"
        assert query.endswith(b"\x00\x00\x01\x00\x01")

    def test_follows_cname_and_compression(self):
        query = build_query("entry.example.net", 7)
        response = make_response(
            query, ["192.0.2.1", "192.0.2.2"], cname="edge.example.com"
        )
        assert parse_a_records(response, 7) == ["192.0.2.1", "192.0.2.2"]

    def test_nxdomain(self):
        query = build_query("dead.example.net", 7)
        with pytest.raises(LookupError, match="NXDOMAIN"):
            parse_a_records(make_response(query, rcode=3), 7)

    def test_empty_answer(self):
        query = build_query("entry.example.net", 7)
        with pytest.raises(LookupError, match="no A record"):
            parse_a_records(make_response(query), 7)

    def test_id_mismatch(self):
        query = build_query("entry.example.net", 7)
        with pytest.raises(ValueError, match="does not match"):
            parse_a_records(make_response(query, ["192.0.2.1"], qid=8), 7)


class TestResolveA:
    def test_doh(self, monkeypatch):
        doh = FakeDoH({"entry.example.net": ["192.0.2.1"]})
        monkeypatch.setattr(resolver.requests, "get", doh)

        assert resolve_a("doh.example.org/dns-query", "entry.example.net") == [
            "192.0.2.1"
        ]
        [(url, host, headers, query)] = doh.calls
        assert (url, host) == (DOH, "entry.example.net")
        assert headers["Accept"] == "application/dns-message"
        assert struct.unpack_from("!H", query)[0] == 0

    def test_udp(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(("127.0.0.1", 0))
        server.settimeout(5)
        seen = []

        def serve():
            query, addr = server.recvfrom(512)
            seen.append(query_host(query))
            server.sendto(make_response(query, ["192.0.2.9"]), addr)

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            port = server.getsockname()[1]
            assert resolve_a(f"127.0.0.1:{port}", "entry.example.net") == ["192.0.2.9"]
        finally:
            thread.join()
            server.close()
        assert seen == ["entry.example.net"]

    def test_retries_transport_errors_only(self, monkeypatch):
        doh = FakeDoH({"entry.example.net": ["192.0.2.1"]})
        outcomes = [requests.ConnectionError("reset"), None]

        def flaky(*args, **kwargs):
            error = outcomes.pop(0)
            if error:
                raise error
            return doh(*args, **kwargs)

        monkeypatch.setattr(resolver.requests, "get", flaky)
        assert resolve_a(DOH, "entry.example.net") == ["192.0.2.1"]
        assert outcomes == []

        nx = FakeDoH({})
        monkeypatch.setattr(resolver.requests, "get", nx)
        with pytest.raises(LookupError):
            resolve_a(DOH, "dead.example.net")
        assert [host for _, host, _, _ in nx.calls] == ["dead.example.net"]


POLICY = [{"dns": {"nameserver-policy": {"*.example.net": DOH}}}]
FORWARDS = [
    "forward=trojan://pw@entry.example.net:443?serverName=x&skipVerify=true#a",
    "forward=trojan://pw@entry.example.net:8443?skipVerify=true#b",
    "forward=trojan://pw@dead.example.net:443?skipVerify=true#c",
    "forward=ss://aes-256-gcm:pw@other.example.com:443#d",
    "forward=ss://aes-256-gcm:pw@192.0.2.50:443#e",
]


class TestPinForwarderHosts:
    def test_forward_hosts(self):
        assert forward_hosts(FORWARDS) == [
            "dead.example.net",
            "entry.example.net",
            "other.example.com",
        ]

    def test_pins_covered_hosts_and_skips_failures(self, caplog):
        calls = []

        def resolve(server, host):
            calls.append((server, host))
            if host == "dead.example.net":
                raise LookupError("NXDOMAIN")
            return ["192.0.2.1", "192.0.2.2"]

        with caplog.at_level(logging.INFO, logger="medusa.core.resolver"):
            records = pin_forwarder_hosts(FORWARDS, POLICY, resolve=resolve)

        assert records == ["dnsrecord=entry.example.net/192.0.2.1"]
        assert calls == [(DOH, "dead.example.net"), (DOH, "entry.example.net")]
        warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
        assert any(
            "Not pinning dead.example.net" in m and "NXDOMAIN" in m for m in warnings
        )
        assert any(
            "Pinned 1 forwarder host(s)" in m and "1 failed" in m for m in warnings
        )

    def test_falls_back_to_next_server(self):
        policy = [{"dns": {"nameserver-policy": {"+.example.net": ["s1", "s2"]}}}]

        def resolve(server, host):
            if server == "s1":
                raise requests.Timeout("timed out")
            return ["192.0.2.3"]

        records = pin_forwarder_hosts(FORWARDS[:1], policy, resolve=resolve)
        assert records == ["dnsrecord=entry.example.net/192.0.2.3"]

    def test_unexpected_errors_do_not_escape(self):
        def resolve(server, host):
            raise RuntimeError("boom")

        assert pin_forwarder_hosts(FORWARDS, POLICY, resolve=resolve) == []

    def test_no_policy_resolves_nothing(self):
        def resolve(server, host):
            raise AssertionError("should not resolve")

        assert pin_forwarder_hosts(FORWARDS, [{"dns": {}}], resolve=resolve) == []


class TestOutputLayout:
    def write(self, tmp_path, records):
        out = tmp_path / "glider.conf"
        GenerateCommand()._write_output_file(
            str(out), "glider", ["forward=x://h:1"], "R.rule", records
        )
        return out.read_text()

    def test_no_records_keeps_previous_layout(self, tmp_path):
        template = TEMPLATE.read_text()
        assert (
            self.write(tmp_path, [])
            == template + "\nrulefile=R.rule\n\nforward=x://h:1\n"
        )

    def test_records_between_template_and_rulefile(self, tmp_path):
        template = TEMPLATE.read_text()
        text = self.write(tmp_path, ["dnsrecord=a.example.net/192.0.2.1"])
        assert text.startswith(template)
        tail = text[len(template) :].splitlines()
        assert tail == [
            "",
            "",
            "# Forwarder hosts resolved by the subscription's nameserver-policy "
            "DNS at generation time",
            "dnsrecord=a.example.net/192.0.2.1",
            "",
            "rulefile=R.rule",
            "",
            "forward=x://h:1",
        ]


class FakeFetcher:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def fetch(self, url):
        lines = [
            "trojan://pw@entry.example.net:443?sni=x#a",
            "trojan://pw@dead.example.net:443#c",
        ]
        return base64.b64encode("\n".join(lines).encode())

    def fetch_clash_config(self, url):
        return POLICY[0]


def test_generate_end_to_end(tmp_path, monkeypatch):
    doh = FakeDoH({"entry.example.net": ["192.0.2.1"]})
    monkeypatch.setattr(resolver.requests, "get", doh)
    monkeypatch.setattr("medusa.cli.commands.URLFetcher", FakeFetcher)
    config = tmp_path / "config.yml"
    config.write_text("subscriptions: [https://sub.example.org/x]\n")
    out = tmp_path / "glider.conf"

    GenerateCommand().execute(str(out), "glider", str(config))

    text = out.read_text()
    assert text.startswith(TEMPLATE.read_text())
    assert "dnsrecord=entry.example.net/192.0.2.1\n" in text
    assert "dead.example.net/" not in text
    assert text.index("dnsrecord=") < text.index("rulefile=")
    assert "forward=trojan://pw@dead.example.net:443" in text
    assert sorted(host for _, host, _, _ in doh.calls) == [
        "dead.example.net",
        "entry.example.net",
    ]
    assert {url for url, _, _, _ in doh.calls} == {DOH}
