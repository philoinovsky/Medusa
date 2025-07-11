"""CLI argument parsing."""

import argparse


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="medusa",
        description="Medusa - Config generator for proxy tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  medusa -o glider.conf
  medusa -o glider.conf --backend glider
  medusa -o output.conf --backend glider --verbose
        """
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output configuration file path"
    )
    
    parser.add_argument(
        "--backend",
        type=str,
        default="glider",
        help="Target backend (default: glider)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.yml",
        help="Configuration file name (default: config.yml)"
    )
    
    return parser


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = create_parser()
    return parser.parse_args()