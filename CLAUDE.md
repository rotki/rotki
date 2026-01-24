# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rotki is a privacy-focused crypto portfolio management and tax reporting application with:
- **Python backend** (Flask API, accounting engine, blockchain interactions)
- **Vue.js/TypeScript frontend** (Electron desktop app + web interface)
- **Rust service** (Colibri - performance-critical components)

### Fork Purpose: Stacks Integration

This fork adds first-class Stacks blockchain support including:
- Native STX tracking and balance queries
- SIP-10 token support (sBTC, stSTX, stSTXBTC, etc.)
- Full transaction history and decoding
- sBTC bridge operations (BTC<->sBTC pegin/pegout)
- Stacking and liquid staking protocol support
- Price feeds for tax preparation

### CRITICAL: Fork-Only Development

**ALL work happens on this fork (alexlmiller/rotki), NOT upstream (rotki/rotki).**

- All commits, branches, issues, and PRs target this fork
- Never push to or create issues/PRs on upstream without explicit permission
- If upstream interaction is requested, ALWAYS confirm before proceeding
- Use `origin` (the fork) for all git operations, not `upstream`

```bash
# Correct - pushes to fork
git push origin develop

# WRONG - never do this without explicit confirmation
git push upstream develop
```

## Development Commands

### Prerequisites
- Node.js 22+, pnpm 10+
- Python 3.11+
- Rust (stable toolchain)
- uv (https://docs.astral.sh/uv/)

### Quick Start
```bash
# Install JS dependencies at repo root
pnpm install

# (Python) Create/sync virtual env via uv
uv sync

# Run full development environment (frontend + backend + colibri)
pnpm dev

# Run web-only development (no Electron)
pnpm dev:web
```

### Backend Development
```bash
# Run backend server
uv run python -m rotkehlchen --api-port 4242 --websockets-port 4333

# Run all backend tests
uv run python pytestgeventwrapper.py

# Run specific test file
uv run python pytestgeventwrapper.py rotkehlchen/tests/api/test_assets.py

# Run specific test
uv run python pytestgeventwrapper.py rotkehlchen/tests/api/test_assets.py::test_add_user_asset

# Filter tests with -k
uv run python pytestgeventwrapper.py -k add_user_asset

# Lint Python code
uv run make lint

# Format Python code
uv run make format
```

### Frontend Development
**IMPORTANT: All frontend commands should be run from the `frontend/` directory, NOT `frontend/app/`**

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm run lint:fix
pnpm run dev
pnpm run build
pnpm run test:unit
pnpm run typecheck
pnpm run clean:modules  # If build fails
```

### Colibri (Rust) Service
```bash
cd colibri
cargo build
cargo run -- --database ../data/global.db --port 4343
```

## Code Architecture

### Backend Structure
- `rotkehlchen/` - Main Python package
  - `api/` - REST API and WebSocket handlers
  - `chain/` - Blockchain integrations (Ethereum, Bitcoin, L2s)
  - `exchanges/` - Exchange integrations (Binance, Kraken, etc.)
  - `accounting/` - Tax calculation and accounting logic
  - `db/` - Database layer with SQLite
  - `externalapis/` - External service integrations
  - `globaldb/` - Global assets database management
  - `history/events/` - Core event abstraction for all activities

### Frontend Structure
- `frontend/app/` - Vue.js Electron application
  - `src/` - Application source code
    - `components/` - Reusable Vue components
    - `pages/` - Route pages
    - `composables/` - Vue composition API utilities
    - `store/` - Pinia state management
  - `electron/` - Electron main process code
  - `tests/` - Test suites

### Key Architectural Patterns
1. **API Communication**: Frontend communicates with backend via REST API (port 4242) and WebSockets (port 4333)
2. **Database**: SQLite for user data, separate global database for assets
3. **State Management**: Pinia stores in frontend, coordinated with backend state
4. **Event System**: `HistoryBaseEntry` is the core abstraction for all blockchain/exchange activities
5. **Plugin Architecture**: Modular design for adding new blockchains and exchanges

## Frontend Development Guidelines

See `.claude/rules/frontend-conventions.md` for detailed TypeScript examples.

### Core Rules
- **Use `get()` and `set()` from VueUse** instead of `.value` when working with refs
- **Explicit types required**: `ref<boolean>(false)`, `computed<string>(() => ...)`, explicit function return types
- **Floating promises**: Use `startPromise()` from `@shared/utils`, never `void`
- **useI18n**: Always use `{ useScope: 'global' }` parameter
- **Props**: Use `defineProps<{}>()` generic syntax
- **Styling**: Tailwind CSS only; scoped CSS modules only for TransitionGroup animations
- **Localization**: Keys in en.json etc. should be ordered alphabetically

### Code Organization
- Split complex logic into focused composables
- Each composable should have single responsibility
- Prioritize readability over brevity

### Testing
- Run tests: `pnpm run test:unit` from `frontend/` directory
- Vitest for unit tests, Playwright for E2E
- Test files colocated: `use-balances-store.ts` → `use-balances-store.spec.ts`

## Backend Conventions

See `.claude/rules/backend-conventions.md` for detailed EVM decoder patterns.

### Exchange Addition
Add exchanges under `exchanges/` directory (reference: `bitfinex.py`). Implement:
- API key/secret authentication
- Balance queries
- Deposits/withdrawals (asset movements)
- Trade history
- Tests with mocked data

### EVM Protocol Decoders
Inherit from `DecoderInterface`, name class `ModulenameDecoder`. Implement:
- `counterparties()` - Protocol names like `uniswap-v1`, `makerdao_dsr`
- `addresses_to_decoders()` - Map contracts to decode functions (optional)
- `decoding_rules()` - Functions for all decoding (optional)
- `enricher_rules()` - Enrich existing events (optional)

### Python Conventions
- Byte signatures as constant literals: `TOPIC: Final = b'\xdc\xbc...'`
- Don't use asset objects as constants; use identifier strings
- Always use `Final` type specifier for constants
- All EVM address literals must be checksummed

## Testing Strategy

### Backend Testing
- Always run through `pytestgeventwrapper.py` (gevent async)
- Fixtures in `rotkehlchen/tests/fixtures/`
- Mock external APIs for deterministic tests
- EVM addresses must be checksummed (use `to_checksum_address()`)
- Do not add `@pytest.mark.vcr` to decoder tests
- Etherscan: Use `ETHERSCAN_API_KEY` env var with v2 API (`https://api.etherscan.io/v2/api?chainid=${chainid}`)

### Frontend Testing
- Vitest with Vue Test Utils
- Playwright for E2E
- Follow patterns in `frontend/app/tests/`

## Code Review Guidelines

### No Assumptions Policy
- Do NOT assume error handling is missing without tracing implementations
- Do NOT assume validation is missing without checking type definitions
- ALWAYS trace function calls to actual implementations

### Known Safe Functions (internal error handling)
- `request_get()` - HTTP wrapper handles errors internally
- `globaldb_get_*()` - Database functions with built-in handling
- `get_or_create_evm_asset()` - Asset creation with validation
- Functions from `rotkehlchen.utils.network`

### Pre-validated Types (no runtime validation needed)
- `ChainID` - Enum with compile-time validation
- `ChecksumEvmAddress` - Validated on construction
- `Asset`, `TimestampMS` - Type-safe representations
- `Final` typed constants are immutable

### Evidence-Based Review
For each issue: provide exact code line, trace full path, check utility functions, verify type guarantees.

### Common False Positives to Avoid
- Missing try-catch around `request_get()`
- ChainID validation (it's an enum)
- KeyError without checking try-except blocks
- Error handling that exists in called functions

### Systematic Review Process
1. Check pending review comments first
2. Line-by-line examination
3. Error handling verification (KeyError, IndexError, API responses)
4. Code efficiency (redundant operations, optimizable conditions)
5. Logging completeness
6. Style and formatting
7. Edge case analysis (empty inputs, None values, bounds)
8. Test coverage

## Common Issues & Solutions

- **Frontend build fails**: Run `pnpm run clean:modules` then `pnpm install --frozen-lockfile`
- **Backend gevent errors**: Always use `pytestgeventwrapper.py`, never direct pytest
- **"Invalid XXX account in DB"**: Address not checksummed - use `to_checksum_address()`
- **WebSocket connection issues**: Check ports 4242 (API) and 4333 (WS) are free

## Commits and PRs

- Commit titles should not exceed 50 characters
- Give description in short title; add blank line and elaborate if needed
- Commits should do one thing
- Do not add Co-Authored-By entries for any AI tool
- Target `bugfixes` branch for patches, `develop` for features

## Memories

- EVM addresses MUST be checksummed:
  - CORRECT: `'0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'`
  - WRONG: `'0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c'`
- If you see "Invalid XXX account in DB" it's almost certain the address is not checksummed
- `string_to_evm_address()` is just a no-op typing function - it will NOT checksum the address

## Contribution Guide

See: https://docs.rotki.com/contribution-guides/contribute-as-developer.html

## Important Configuration Files

- `pyproject.toml` - Python project configuration, linting rules
- `frontend/app/package.json` - Frontend dependencies and scripts
- `Makefile` - Common development tasks
- `.github/workflows/` - CI/CD pipelines

## Additional Documentation

Detailed guides in `.claude/rules/`:
- `frontend-conventions.md` - Full TypeScript examples and patterns
- `backend-conventions.md` - EVM decoder details, exchange guide
- `stacks-integration.md` - Stacks blockchain and bridge patterns
