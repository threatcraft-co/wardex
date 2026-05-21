# Contributing to wardex

Thanks for your interest in contributing.

## Development setup

```bash
git clone https://github.com/threatcraft-co/wardex.git
cd wardex
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Code style

We use `ruff` for linting and formatting:

```bash
ruff check .
ruff format .
```

## Reporting issues

- **Bug reports**: include macOS version, VS Code version, and relevant log lines from `~/Library/Logs/wardex.log`
- **False positives**: a legitimate extension was blocked — include the publisher and extension ID
- **Policy requests**: ideas for new policy primitives or detection signals

## Pull requests

- One feature or fix per PR
- Add tests for new logic
- Update docs if behavior changes
- Sign your commits

## Security

Do not file security issues as public GitHub issues. Email `threatcraft@proton.me`.
