# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Rotki is a privacy-first portfolio tracking and accounting tool that supports multiple blockchains and exchanges. It consists of:
- Python backend (Flask-based REST API)
- Vue 3 + TypeScript frontend (web and Electron desktop)
- Rust service (Colibri) for high-performance operations
- SQLCipher for encrypted local storage

## Development Commands

### Quick Start
```bash
# From frontend directory - starts backend, frontend, and colibri
pnpm run --filter . start:dev

# Web-only mode (no Electron)
pnpm run --filter . start:dev --web
```

### Backend Development
```bash
# Create virtual environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements_dev.txt

# Run backend directly
python -m rotkehlchen --rest-api-port 4242

# Run tests (uses custom pytest wrapper for gevent)
python pytestgeventwrapper.py

# Run specific test
python pytestgeventwrapper.py rotkehlchen/tests/path/to/test.py::test_function_name

# Linting and formatting
make lint
make format
```

### Frontend Development
```bash
# From frontend directory
pnpm install

# Development server
pnpm run serve

# Electron development
pnpm run electron:serve

# Run unit tests
pnpm run test:unit

# Run E2E tests
pnpm run cypress:run

# Build for production
pnpm run build
pnpm run electron:build
```

### Database Commands
```bash
# Create test user database
python tools/scripts/create_test_user_db.py

# Database upgrades are handled automatically
```

## Architecture Overview

### Backend Structure
- `rotkehlchen/` - Main backend package
  - `api/` - REST API endpoints and WebSocket handlers
  - `chain/` - Blockchain integrations (Ethereum, Bitcoin, L2s)
  - `exchanges/` - Exchange integrations
  - `accounting/` - PnL calculations and tax reporting
  - `db/` - Database layer with SQLCipher
  - `history/` - Transaction history management
  - `tasks/` - Background task system using gevent
  - `globaldb/` - Shared asset/price database

### Frontend Structure
- `frontend/app/` - Main Vue application
  - `src/pages/` - Route components
  - `src/components/` - Reusable components
  - `src/composables/` - Vue composition API utilities
  - `src/store/` - Pinia state management
  - `electron/` - Electron main process code

### Key Patterns
1. **History Events**: All blockchain transactions are converted to a unified HistoryEvent format
2. **Task Manager**: Background tasks use gevent greenlets for concurrent operations
3. **Database Migrations**: Automatic schema upgrades in `db/upgrades/`
4. **API Versioning**: REST API uses `/api/1/` prefix
5. **Privacy First**: All data stored locally with optional premium sync

## Testing Approach
- Backend uses pytest with custom gevent wrapper
- Frontend uses Vitest for unit tests and Cypress for E2E
- Integration tests in `rotkehlchen/tests/integration/`
- API tests in `rotkehlchen/tests/api/`
- Mock data and fixtures in `tests/fixtures/`

## Git Workflow
- Main branch: `develop`
- Bugfix branch: `bugfixes`
- Use conventional commits (lowercase preferred)
- Don't include "generated with claude" in commit messages
- Add `[skip ci]` to every commit message

## Important Notes
- The project uses SQLCipher for encrypted databases - handle database connections carefully
- WebSocket connections are used for real-time updates
- Exchange APIs have rate limits - respect them in implementations
- History events are the core abstraction for all transaction data
- Always run linting before commits: `make lint`