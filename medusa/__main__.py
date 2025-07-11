"""Medusa main entry point."""

import logging
import sys

from medusa.cli.parser import parse_args
from medusa.cli.commands import GenerateCommand
from medusa.utils.logging import setup_logger
from medusa.utils.exceptions import MedusaError


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Setup logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        setup_logger(level=log_level)
        
        # Execute generate command
        command = GenerateCommand()
        command.execute(
            output_path=args.output,
            backend=args.backend,
            config_file=args.config
        )
        
        return 0
        
    except MedusaError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
