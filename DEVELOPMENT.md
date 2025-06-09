# Development Guide

This guide explains how to set up a development environment for Rotki using `uv`.

## Prerequisites

- Python 3.11.x
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Installing uv

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Or using pipx
pipx install uv
```

## Setting up the development environment

### Using virtual environments (recommended)

1. Clone the repository:
```bash
git clone https://github.com/rotki/rotki.git
cd rotki
```

2. Create a virtual environment and install dependencies:
```bash
# This will create a virtual environment and install all dependencies
uv sync

# To install with development dependencies
uv sync --group dev

# To install with specific dependency groups
uv sync --group dev --group lint --group docs

# To install all dependency groups
uv sync --all-groups
```

3. Activate the virtual environment:
```bash
# The virtual environment is created at .venv
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate  # On Windows
```

### Generating lockfile

If you need to regenerate the lockfile after updating dependencies:

```bash
uv lock
```

## Available dependency groups

- `dev`: Testing and development tools (pytest, coverage, etc.)
- `lint`: Linting tools (mypy, ruff, pylint, pyright)
- `docs`: Documentation generation tools (sphinx)
- `packaging`: Packaging tools
- `profiling`: Profiling tools
- `crossbuild`: Cross-building dependencies for macOS

## Common commands

### Running tests
```bash
uv run pytest rotkehlchen/tests/
# or if venv is activated
pytest rotkehlchen/tests/
```

### Running linting
```bash
uv run ruff check rotkehlchen/ --fix --unsafe-fixes
# or
make lint
```

### Building the package
```bash
uv run python package.py --build full
```

## Updating dependencies

To update dependencies, modify the `pyproject.toml` file and run:
```bash
uv sync
```

To add a new dependency:
```bash
# Add to main dependencies
uv add package-name

# Add to a specific group
uv add --group dev package-name
```

## Notes

- The project uses Python 3.11 exclusively
- The `uv.lock` file ensures reproducible builds
- The `urllib3==2.4.0` override is necessary for compatibility with vcrpy