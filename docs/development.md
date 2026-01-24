# Rotki Development Guide

This guide covers setting up a local development environment for the Rotki fork with Stacks integration.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 22+ | Frontend build and tooling |
| pnpm | 10+ | Package management |
| Python | 3.11+ | Backend runtime |
| uv | Latest | Python dependency management |
| Rust | Stable | Colibri service |

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

### Full Stack (Recommended)

```bash
# Install dependencies
pnpm install

# Run everything: frontend + backend + colibri
pnpm dev
```

Access the app at `http://localhost:5173` (Vite dev server with hot reload).

### Web Only (No Electron)

```bash
pnpm dev:web
```

## Component-by-Component Setup

### Backend

```bash
# Create virtual environment and install dependencies
uv sync

# Run backend server
uv run python -m rotkehlchen --api-port 4242 --websockets-port 4333
```

### Frontend

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm run dev
```

### Colibri (Rust Service)

```bash
cd colibri
cargo build
cargo run -- --database ../data/global.db --port 4343
```

## Running Tests

### Backend Tests

```bash
# All tests (use the wrapper for gevent async)
uv run python pytestgeventwrapper.py

# Specific file
uv run python pytestgeventwrapper.py rotkehlchen/tests/api/test_assets.py

# Specific test
uv run python pytestgeventwrapper.py rotkehlchen/tests/api/test_assets.py::test_add_user_asset

# Filter by keyword
uv run python pytestgeventwrapper.py -k add_user_asset
```

### Frontend Tests

```bash
cd frontend
pnpm run test:unit
```

## Linting and Formatting

### Backend

```bash
uv run make lint    # Check for issues
uv run make format  # Auto-fix formatting
```

### Frontend

```bash
cd frontend
pnpm run lint:fix   # ESLint + auto-fix
pnpm run typecheck  # TypeScript type checking
```

## Local Docker Builds

```bash
# Build image locally
docker build -t rotki-local .

# Run local build
docker run -d -p 8080:80 -v rotki-data:/data rotki-local
```

## Git Workflow

### Branches

| Pattern | Purpose |
|---------|---------|
| `develop` | Main development branch |
| `feat/<name>` | New features |
| `fix/issue-<N>` | Bug fixes |
| `docs/<topic>` | Documentation |

### Using Worktrees

For parallel development or when multiple agents work simultaneously:

```bash
# Create worktree for a feature
git worktree add .worktrees/feat-my-feature -b feat/my-feature
cd .worktrees/feat-my-feature

# After PR is merged
git worktree remove .worktrees/feat-my-feature
git branch -d feat/my-feature
```

### Commits

- Keep commit titles under 50 characters
- Use imperative mood ("Add feature" not "Added feature")
- Target `develop` for features, `bugfixes` for patches

## Common Issues

### Frontend build fails

```bash
cd frontend
pnpm run clean:modules
pnpm install --frozen-lockfile
```

### Backend gevent errors

Always use `pytestgeventwrapper.py` instead of running pytest directly.

### "Invalid XXX account in DB"

EVM addresses must be checksummed. Use `to_checksum_address()`:

```python
from eth_utils import to_checksum_address
address = to_checksum_address('0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c')
```

### WebSocket connection issues

Ensure ports 4242 (API) and 4333 (WebSocket) are not in use:

```bash
lsof -i :4242
lsof -i :4333
```

## Additional Resources

- [Contribution Guide](https://docs.rotki.com/contribution-guides/contribute-as-developer.html)
- [API Documentation](api.rst)
- [Docker Deployment](deployment.md)
