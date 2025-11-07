# AGENTS.md

This file provides guidance for AI coding assistants (e.g., OpenAI Codex CLI, Claude Code, GitHub Copilot Chat) working with code in this repository. It mirrors the content of `CLAUDE.md` with model‑neutral language and a few clarifications useful to any assistant.

## Project Overview

Rotki is a privacy-focused crypto portfolio management and tax reporting application with:
- **Python backend** (Flask API, accounting engine, blockchain interactions)
- **Vue.js/TypeScript frontend** (Electron desktop app + web interface)
- **Rust service** (Colibri - performance-critical components)

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
# Navigate to frontend directory first
cd frontend

# Install dependencies
pnpm install --frozen-lockfile

# Lint and fix
pnpm run lint:fix

# Run the app
pnpm run dev

# Clean frontend modules
pnpm run clean:modules

# Build frontend
pnpm run build

# Run tests
pnpm run test:unit

# Type check
pnpm run typecheck
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
  - `history/` - Transaction and event history handling

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
4. **Event System**: History events are the core abstraction for all blockchain/exchange activities
5. **Plugin Architecture**: Modular design for adding new blockchains and exchanges

## Developing

### Frontend Development Guidelines

#### Directory Structure
- All frontend commands should be run from `frontend/` directory, NOT `frontend/app/`
- The main application code is in `frontend/app/src/`

### Code Organization & Maintainability

- **Split complex logic**: Break down large templates and script logic into smaller, focused composables
- **Component decomposition**: Split large components into smaller, reusable sub-components
- **Logical separation**: Each composable should have a single, well-defined responsibility
- **Maintainability focus**: Prioritize code readability and maintainability over brevity

#### Vue.js and TypeScript Conventions
- Use VueUse utilities for reactive state management
- **IMPORTANT: Use `get()` and `set()` from VueUse instead of `.value` when working with refs**

#### Explicit TypeScript Typing Requirements

- **Always use explicit types for refs**: `ref<boolean>(false)` instead of `ref(false)`
- **Always use explicit types for computed**: `computed<boolean>(() => ...)` instead of `computed(() => ...)`
- **Always return explicit types from functions**: `function getName(): string { ... }`
- **Always type reactive variables**: `const isLoading = ref<boolean>(false)`
- **Always type computed properties**: `const fullName = computed<string>(() => ...)`

#### Correct Examples:

```typescript
// ✅ Correct - Explicit typing with VueUse get/set
import { get, set } from '@vueuse/shared';

const isVisible = ref<boolean>(true);
const count = ref<number>(0);
const items = ref<string[]>([]);
const user = ref<User>();

const isEven = computed<boolean>(() => get(count) % 2 === 0);
const formattedName = computed<string>(() => `${get(firstName)} ${get(lastName)}`);

function getUserById(id: number): User | undefined {
  return get(users).find(user => user.id === id) || undefined;
}

function updateCount(newValue: number): void {
  set(count, newValue);
}

async function fetchData(): Promise<ApiResponse> {
  return await $fetch('/api/data');
}
```

#### Incorrect Examples:

```typescript
// ❌ Incorrect - Missing explicit types
const isVisible = ref(true);
const count = ref(0);
const items = ref([]);
const user = ref();

const isEven = computed(() => count.value % 2 === 0);
const formattedName = computed(() => `${firstName.value} ${lastName.value}`);

function getUserById(id: number) {
  return users.value.find(user => user.id === id) || undefined;
}

async function fetchData() {
  return await $fetch('/api/data');
}
```

- VueUse utilities like `get()`, `set()`, `toRefs()`, `computed()` etc. are auto-imported
- Use Pinia for state management - stores are in `frontend/app/src/store/`
- TypeScript is strict - ensure proper typing

#### Setup Script Organization (Preferred Order)
1. Imports
2. Definitions (`defineProps`, `defineEmits`, etc.)
3. I18n & vue-router
4. Reactive state variables
5. Pinia stores
6. Composables
7. Computed properties
8. Methods
9. Watchers
10. Lifecycle hooks
11. Exposed methods

#### Component Conventions
- Use `defineProps<{}>()` instead of `defineProps({})`
- Simplified emit definitions:
  ```typescript
  const emit = defineEmits<{
    'update:msg': [msg: string];
  }>();
  ```
- Use `$style` in templates instead of `useCssModules`
- Use `$attrs` in templates instead of `useAttrs`

#### Pinia Store Structure
1. State definitions
2. Computed getters
3. Actions
4. Optional watchers

#### Styling
- Transitioning from scoped SCSS with BEM to tailwind
- Follow existing patterns for consistency

#### Localization
- For the localization files (en.json, es.json, etc.), the keys should be ordered alphabetically.

#### Testing
- Run tests with `pnpm run test:unit` from `frontend/` directory
- Use Vitest for unit tests with Vue Test Utils
- **Unit test file naming**: `.spec.ts` files should follow the naming of the tested file and be located in the same folder
  ```
  // Example structure:
  src/modules/balances/use-balances-store.ts
  src/modules/balances/use-balances-store.spec.ts

  src/composables/accounts/use-account-import-export.ts
  src/composables/accounts/use-account-import-export.spec.ts
  ```
- Component tests should follow existing patterns in `frontend/app/tests/` and `*.spec.ts`

### Contribution guide

The contribution guide can be seen here: https://docs.rotki.com/contribution-guides/contribute-as-developer.html

### Exchange Addition

- To add an exchange you will need to add the new exchange under the `exchanges/` directory. A nice example is bitfinxex.py
- For each exchange you need to implement the basic method of the `ExchangeInterface` superclass:
  - Authentication for the api key/secret whatever the exchange API uses.
  - Fetch balances from the exchange
  - Fetch deposits/withdrawals (also called asset movements) and trades.
- You will need to create some tests with mocked data

### Adding EVM protocol decoders

As an example decoder, we can look at [MakerDAO](https://github.com/rotki/rotki/blob/1039e04304cc034a57060757a1a8ae88b3c51806/rotkehlchen/chain/ethereum/modules/makerdao/decoder.py).

It needs to contain a class that inherits from the `DecoderInterface` and is named `ModulenameDecoder`.

Note: If your new decoder decodes an airdrop's claiming event and this airdrop is present in the [data repo airdrop index](https://github.com/rotki/data/blob/develop/airdrops/index_v2.json) with `has_decoder` as `false`, please update that also.

#### Counterparties

It needs to implement a method called `counterparties()` which returns a list of counterparties that can be associated with the transactions of this module. Most of the time these are protocol names like `uniswap-v1`, `makerdao_dsr`, etc.

These are defined in the `constants.py` file.

#### Mappings and rules

The `addresses_to_decoders()` method maps any contract addresses that are identified in the transaction with the specific decoding function that can decode it. This is optional.

The `decoding_rules()` define any functions that should simply be used for all decoding so long as this module is active. This is optional.

The `enricher_rules()` define any functions that would be used as long as this module is active to analyze already existing decoded events and enrich them with extra information we can decode thanks to this module. This is optional.

#### Decoding explained

In very simple terms, the way the decoding works is that we go through all the transactions of the user and we apply all decoders to each transaction event that touches a tracked address. The first decoder that matches creates a decoded event.

The event creation consists of creating a `HistoryBaseEntry`. These are the most basic form of events in rotki and are used everywhere. The fields as far as decoded transactions are concerned are explained below:

- `group_identifier` is always the transaction hash. This identifies history events in the same transaction.
- `sequence_index` is the order of the event in the transaction. Many times this is the log index, but decoders tend to play with this to make events appear in a specific way.
- `asset` is the asset involved in the event.
- `balance` is the balance of the involved asset.
- `timestamp` is the Unix timestamp **in milliseconds**.
- `location` is the location. Almost always `Location.BLOCKCHAIN` unless we got a specific location for the protocol of the transaction.
- `location_label` is the initiator of the transaction.
- `notes` is the human-readable description to be seen by the user for the transaction.
- `event_type` is the main type of the event. (see next section)
- `event_subtype` is the subtype of the event. (see next section)
- `counterparty` is the counterparty/target of the transaction. For transactions that interact with protocols, we tend to use the `CPT_XXX` constants here.

#### Event type/subtype and counterparty

Each combination of event type and subtype and counterparty creates a new unique event type. This is important as they are all treated differently in many parts of rotki, including the accounting. But most importantly this is what determines how they appear in the UI!

The mapping of these HistoryEvents types, subtypes, and categories is done in [rotkehlchen/accounting/constants.py](https://github.com/rotki/rotki/blob/17b4368bc15043307fa6acf536b5237b3840c40e/rotkehlchen/accounting/constants.py).

#### Things to keep in mind

- All byte signatures should be a constant byte literal. Like ```DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'```
- Don't put assets as constants. If you need a constant just use the asset identifier as a string and compare against it.

## Testing Strategy

### Backend Testing
- Uses pytest with gevent for async testing
- Extensive fixtures in `rotkehlchen/tests/fixtures/`
- Mock external APIs for deterministic tests
- Database fixtures for integration testing
- Make sure that all EVM addresses constant literals you add in the code are properly checksummed. The output of to_checksum_address() is what they should be. Do not use string_to_evm_address(). This does not checksum the address.
- Do not VCR tests. Let the human developers do it. That means do not put `@pytest.mark.vcr` on any decoder tests you write.
- For Etherscan use the api key from ETHERSCAN_API_KEY env variable and use etherscan v2. It's as v1 but using https://api.etherscan.io/v2/api?chainid=${chainid} . As described here: https://docs.etherscan.io/etherscan-v2. If there is no API key in the env variable then prompt the user for it when you need to query etherscan.

### Frontend Testing
- Vitest for unit tests with Vue Test Utils
- Component tests should follow existing patterns in `frontend/app/tests/` and `*.spec.ts`

## Packaging
```bash
# Package for distribution (requires proper environment setup)
python package.py
```

## Important Configuration Files
- `pyproject.toml` - Python project configuration, linting rules
- `frontend/app/package.json` - Frontend dependencies and scripts
- `Makefile` - Common development tasks
- `.github/workflows/` - CI/CD pipelines

## Development Tips
1. Always run through `pytestgeventwrapper.py` for backend tests to ensure proper gevent patching
2. Frontend uses strict TypeScript - ensure types are properly defined
3. Follow existing code patterns - the codebase has established conventions
4. Use the existing test infrastructure - comprehensive fixtures are available
5. WebSocket messages follow specific format - check `api/websockets/typedefs.py`
6. For all python backend constants make sure to use the `Final` type specifier.

## Committing
- Commits should be just to the point, not too long and not too short.
- Commit titles should not exceed 50 characters.
- Give a description of what the commit does in a short title. If more information is needed, then add a blank line and afterward elaborate with as much information as needed.
- Commits should do one thing; if two commits both do the same thing, that's a good sign they should be combined.
- Do not add Co-Authored-By entries for any AI tool.

## Opening PRs
- Do not add Co-Authored-By entries for any AI tool.

## Common Issues & Solutions
- Frontend build fails: Run `pnpm run clean:modules` then `pnpm install --frozen-lockfile`
- Backend gevent errors: Always use `pytestgeventwrapper.py`, never direct pytest
- WebSocket connection issues: Check ports 4242 (API) and 4333 (WS) are free

## Code Review Guidelines

When reviewing rotki code, follow these principles to avoid false positives:

### 1. No Assumptions Policy
- Do NOT assume error handling is missing without tracing function implementations
- Do NOT assume validation is missing without checking type definitions
- Do NOT assume patterns are incorrect without understanding project conventions
- ALWAYS trace function calls to their actual implementations

### 2. Known Safe Functions (with internal error handling)
- `request_get()` - HTTP wrapper that handles all errors internally
- `globaldb_get_*()` - Database functions with built-in error handling
- `get_or_create_evm_asset()` - Asset creation with validation
- Functions from `rotkehlchen.utils.network` generally handle errors

### 3. Pre-validated Types (no runtime validation needed)
- `ChainID` - Enum type with compile-time validation
- `ChecksumEvmAddress` - Validated on construction
- `Asset` - Type-safe asset representation
- `TimestampMS` - Type-safe timestamp
- Any `Final` typed constants are immutable

### 4. Evidence-Based Review Requirements
For each issue identified:
- Provide exact code line showing the problem
- Trace the full code path to verify issue exists
- Check if utility functions handle the concern
- Verify type system doesn't provide guarantees
- Explain why existing code doesn't mitigate it

### 5. Common False Positive Patterns to Avoid
- Flagging missing try-catch around `request_get()`
- Suggesting ChainID validation when it's an enum
- Assuming KeyError isn't caught without checking try-except blocks
- Recommending error handling that exists in called functions

### 6. Systematic Code Review Process
When reviewing code changes, follow this systematic approach:

1. **Check for pending review comments first** - Look for any unresolved comments from repository maintainers or other reviewers
2. **Line-by-line examination** - Read every changed line carefully, don't skim or make assumptions
3. **Error handling verification**:
   - Check if dictionary/list access handles KeyError/IndexError
   - Verify API responses handle missing or malformed data
   - Ensure error paths have appropriate logging
4. **Code efficiency**:
   - Look for unnecessary comparisons or redundant operations
   - Check for optimizable conditions
   - Verify no unnecessary loops or repeated calculations
5. **Logging completeness**:
   - Error conditions should be logged with context
   - Empty else/except blocks should explain why they're empty
6. **Style and formatting**:
   - Check spacing in strings and error messages
   - Verify consistent formatting with project standards
7. **Edge case analysis**:
   - What happens with empty inputs?
   - How are None/null values handled?
   - Are array bounds checked?
8. **Test coverage** - Verify new functionality has appropriate tests

## Memories
- EVM addresses MUST be checksummed:
  ✅ CORRECT: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'
  ❌ WRONG: '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c'
- If you see "Invalid XXX account in DB" it's almost certain the address is not checksummed. Always checksum addresses you use with to_checksum_address
- `string_to_evm_address()` is just a no-op typing function. It will not checksum the literal argument to a checksummed evm address. That means you should make sure to only give checksummed EVM address literals to it
