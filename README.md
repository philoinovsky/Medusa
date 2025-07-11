# Medusa

Medusa is a modern, refactored config generator for proxy tools. It fetches subscription URLs and converts them to proxy configurations with improved security, maintainability, and extensibility.

## Features

- **Secure**: Eliminated `eval()` security vulnerability with proper dispatch system
- **Modular**: Clean separation of concerns with pluggable backends
- **Type-safe**: Full type annotations with Pydantic validation
- **Robust**: Comprehensive error handling and logging
- **Extensible**: Easy to add new proxy types and backends
- **Tested**: Comprehensive test suite with pytest

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Usage

Basic usage:
```bash
medusa -o glider.conf
```

With custom configuration:
```bash
medusa -o output.conf --config my_config.yml --backend glider --verbose
```

## Configuration

Create a `config.yml` file with your subscription URLs:

```yaml
subscriptions:
  - https://example.com/subscription1
  - https://example.com/subscription2
```

## Architecture

The refactored Medusa follows a clean, modular architecture:

```
medusa/
├── cli/           # Command-line interface
├── core/          # Core functionality (fetching, parsing, converting)
├── backends/      # Backend implementations (Glider, etc.)
├── config/        # Configuration management
├── utils/         # Utilities (logging, exceptions)
└── templates/     # Configuration templates
```

### Key Components

- **URLFetcher**: Handles subscription URL fetching with retry logic
- **ContentDecoder**: Multi-strategy content decoding (Base64, plain text)
- **URLParser**: Validates and parses proxy URLs
- **BackendConverter**: Pluggable backend system for different proxy tools
- **ConfigLoader**: Configuration loading with validation

## Supported Backends

- **Glider** (default) - Full support

## Supported Proxy Types

- **Shadowsocks** (ss://) - ✅ Full support
- **Trojan** (trojan://) - ✅ Full support  
- **VMess** (vmess://) - 🚧 Framework ready, implementation pending
- **VLESS** (vless://) - 🚧 Framework ready, implementation pending

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=medusa --cov-report=html
```

### Code Quality

Format code:
```bash
black medusa/ tests/
```

Lint code:
```bash
ruff check medusa/ tests/
```

Type checking:
```bash
mypy medusa/
```

### Adding New Backends

1. Create a new backend class inheriting from `BackendConverter`
2. Implement required methods (`name`, `supported_schemes`, `convert`)
3. Register the backend in `ConverterRegistry`

### Adding New Proxy Types

1. Create a handler class inheriting from `ProxyHandler`
2. Implement the `convert` method for your proxy type
3. Add the handler to the appropriate backend converter

## Migration from v1.x

The refactored version maintains CLI compatibility while providing:

- **Improved Security**: No more `eval()` usage
- **Better Error Handling**: Graceful failure with detailed logging
- **Enhanced Logging**: Structured logging with configurable levels
- **Type Safety**: Full type annotations and validation
- **Modular Design**: Easy to extend and maintain

## License

MIT License