"""Rules extraction from Clash configs."""

from typing import Any, Dict, List, Tuple

from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class RulesExtractor:
    """Extracts DNS and domain rules from Clash-format configs."""

    def extract_dns_rules(
        self, clash_configs: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[str]]]:
        """Extract DNS nameserver-policy entries from Clash configs.

        Each entry maps a DNS server to the domains that should use it.

        Args:
            clash_configs: List of parsed Clash YAML dicts

        Returns:
            List of (dnsserver, [domain, ...]) tuples, deduplicated
        """
        # dnsserver -> set of domains
        dns_map: Dict[str, set] = {}

        for config in clash_configs:
            policy = config.get("dns", {}).get("nameserver-policy", {}) or {}
            for domain_pattern, server in policy.items():
                # Normalize domain: *.example.com / +.example.com -> example.com
                domain = domain_pattern.lstrip("*+").lstrip(".")
                if not domain:
                    continue

                # server can be a string or list
                if isinstance(server, list):
                    server = server[0] if server else None
                if not server:
                    continue

                # Normalize server: strip protocol prefix if present
                server_str = str(server)
                for prefix in ("https://", "http://", "tls://"):
                    if server_str.startswith(prefix):
                        server_str = server_str[len(prefix) :]
                        break

                # Ensure port is present for plain DNS
                if ":" not in server_str and "/" not in server_str:
                    server_str = f"{server_str}:53"

                dns_map.setdefault(server_str, set()).add(domain)

        result = []
        for server, domains in dns_map.items():
            result.append((server, sorted(domains)))

        logger.info(
            f"Extracted {len(result)} DNS rule groups "
            f"from {len(clash_configs)} configs"
        )
        return result

    def format_glider_rules(self, dns_rules: List[Tuple[str, List[str]]]) -> List[str]:
        """Format DNS rules as glider rules file content.

        Args:
            dns_rules: List of (dnsserver, [domain, ...]) tuples

        Returns:
            Lines for the glider rules file
        """
        lines: List[str] = []

        for dnsserver, domains in dns_rules:
            lines.append(f"dnsserver={dnsserver}")
            for domain in domains:
                lines.append(f"domain={domain}")
            lines.append("")

        return lines
