"""CLI command implementations."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from medusa.config.loader import ConfigLoader
from medusa.core.fetcher import URLFetcher
from medusa.core.decoder import ContentDecoder
from medusa.core.parser import URLParser
from medusa.core.converter import ProxyConverter
from medusa.core.rules import RulesExtractor
from medusa.utils.exceptions import MedusaError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class GenerateCommand:
    """Command to generate proxy configuration."""

    def __init__(self):
        """Initialize generate command."""
        self.config_loader = ConfigLoader()
        self.url_parser = URLParser()
        self.decoder = ContentDecoder()
        self.converter = ProxyConverter()
        self.rules_extractor = RulesExtractor()

    def execute(self, output_path: str, backend: str, config_file: str) -> None:
        """Execute the generate command.

        Args:
            output_path: Output file path
            backend: Target backend name
            config_file: Configuration file name

        Raises:
            MedusaError: If generation fails
        """
        try:
            # Load configuration
            config = self.config_loader.load_config(config_file)
            logger.info(f"Loaded {len(config.subscriptions)} subscription URLs")

            # Process all subscriptions
            all_converted = []
            clash_configs: List[Dict[str, Any]] = []
            successful_urls = 0

            with URLFetcher() as fetcher:
                for url in config.subscriptions:
                    try:
                        # Fetch subscription content
                        content = fetcher.fetch(str(url))

                        # Decode content
                        decoded_urls = self.decoder.decode(content)
                        if not decoded_urls:
                            logger.warning(f"No URLs found in subscription: {url}")
                            continue

                        # Parse URLs
                        parsed_urls = self.url_parser.parse_urls(decoded_urls)
                        if not parsed_urls:
                            logger.warning(
                                f"No valid proxy URLs found in subscription: {url}"
                            )
                            continue

                        # Convert to backend format
                        converted = self.converter.convert(backend, parsed_urls)
                        if converted:
                            all_converted.extend(converted)
                            successful_urls += 1
                            logger.info(
                                f"Successfully processed {len(converted)} proxies from {url}"
                            )
                        else:
                            logger.warning(
                                f"No proxies converted from subscription: {url}"
                            )

                    except Exception as e:
                        logger.error(f"Failed to process subscription {url}: {e}")
                        continue

                # Fetch Clash configs for rules extraction
                for url in config.subscriptions:
                    clash_data = fetcher.fetch_clash_config(str(url))
                    if clash_data:
                        clash_configs.append(clash_data)

            # Generate output file
            rules_path = f"{output_path}.rule"
            self._write_output_file(output_path, backend, all_converted, rules_path)

            # Generate rules file
            self._write_rules_file(rules_path, clash_configs)

            if successful_urls > 0:
                logger.info(
                    f"Successfully generated {output_path} with {len(all_converted)} "
                    f"proxy configurations from {successful_urls} subscriptions"
                )
            else:
                logger.warning(
                    f"No valid proxy configurations found. "
                    f"Created {output_path} with template only"
                )

        except Exception as e:
            logger.error(f"Failed to generate configuration: {e}")
            raise MedusaError(f"Configuration generation failed: {e}") from e

    def _write_output_file(
        self,
        output_path: str,
        backend: str,
        converted_configs: List[str],
        rules_path: str,
    ) -> None:
        """Write output configuration file.

        Args:
            output_path: Output file path
            backend: Backend name for template
            converted_configs: List of converted proxy configurations
            rules_path: Path to the rules file (added as rules-file= directive)
        """
        try:
            # Load template
            template_lines = self.config_loader.load_template(backend)

            # Create output directory if it doesn't exist
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(output_file, "w", encoding="utf-8") as f:
                # Write template
                f.writelines(template_lines)

                # Write rules-file reference
                f.write(f"\nrules-file={rules_path}\n\n")

                # Write converted configurations
                for config in converted_configs:
                    f.write(f"{config}\n")

            logger.info(f"Successfully wrote configuration to {output_path}")

        except Exception as e:
            logger.error(f"Failed to write output file {output_path}: {e}")
            raise

    def _write_rules_file(
        self,
        rules_path: str,
        clash_configs: List[Dict[str, Any]],
    ) -> None:
        """Write rules file extracted from Clash configs.

        Args:
            rules_path: Output rules file path
            clash_configs: List of parsed Clash YAML dicts
        """
        if not clash_configs:
            logger.warning("No Clash configs available, skipping rules file")
            return

        try:
            dns_rules = self.rules_extractor.extract_dns_rules(clash_configs)
            if not dns_rules:
                logger.warning("No DNS rules extracted, skipping rules file")
                return

            lines = self.rules_extractor.format_glider_rules(dns_rules)

            rules_file = Path(rules_path)
            rules_file.parent.mkdir(parents=True, exist_ok=True)

            with open(rules_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(f"{line}\n")

            logger.info(f"Successfully wrote rules to {rules_path}")

        except Exception as e:
            logger.error(f"Failed to write rules file {rules_path}: {e}")
            raise
