# Medusa

Config generator for proxy tools. Medusa fetches subscription URLs, decodes their contents, parses proxy URLs (`ss://`, `trojan://`, `anytls://`, `vmess://`, `vless://`), and renders a backend config file. Currently the Glider backend is fully wired; it also produces a companion `.rule` file with DNS nameserver policies extracted from Clash-format subscriptions.

## Installation

```bash
pip install -e .
# with dev tools
pip install -e ".[dev]"
```

Python 3.8+ required.

## Usage

```bash
medusa -o glider.conf
medusa -o glider.conf --backend glider --verbose
medusa -o glider.conf --config my_config.yml
```

Flags:

- `-o, --output` — output file path (required). A `<output>.rule` file is written alongside it.
- `--backend` — target backend (default: `glider`).
- `--config` — config file name or absolute path (default: `config.yml`).
- `-v, --verbose` — verbose logging.

## Configuration

Config files are resolved from `medusa/configs/` unless an absolute path is given. Minimal `config.yml`:

```yaml
subscriptions:
  - https://example.com/subscription1
  - https://example.com/subscription2
```

Each subscription URL is fetched, decoded (Gzip → Base64 → URL-safe Base64 → plain text), and the resulting proxy URLs are converted using the selected backend.

## Output

Running `medusa -o glider.conf` produces:

- `glider.conf` — the backend template (from `medusa/templates/<backend>_template.conf`) followed by a `rulefile=glider.conf.rule` directive and one `forward=...` line per deduplicated proxy.
- `glider.conf.rule` — `dnsserver=` / `domain=` entries built from `dns.nameserver-policy` in the Clash YAML variant of each subscription (when available).

## Supported protocols

| Backend | Shadowsocks | Trojan | AnyTLS | VMess           | VLESS           |
| ------- | ----------- | ------ | ------ | --------------- | --------------- |
| Glider  | ✅          | ✅     | ✅     | not implemented | not implemented |

## Architecture

Pipeline: `CLI → ConfigLoader → URLFetcher → ContentDecoder → URLParser → ProxyConverter → output file` (with `RulesExtractor` producing the rules file in parallel).

```
medusa/
├── cli/        # argparse + GenerateCommand orchestrator
├── core/       # fetcher, decoder, parser, converter, rules
├── backends/   # BackendConverter ABC + per-backend handlers
├── config/     # Pydantic config model + loader
├── configs/    # default config.yml lives here
├── templates/  # <backend>_template.conf files
└── utils/      # logging, exceptions
```

### Extending

- **New backend** — subclass `BackendConverter` in `medusa/backends/`, register it in `ConverterRegistry._register_default_converters()`, and drop a `<name>_template.conf` in `medusa/templates/`.
- **New protocol** — subclass `ProxyHandler` and add it to the backend's `_handlers` dict.

## Development

```bash
pytest                                  # run tests
pytest --cov=medusa --cov-report=html   # with coverage

black medusa/ tests/
ruff check medusa/ tests/
mypy medusa/
```

## License

MIT
