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
- Python 3.14t
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
uv run pytest

# Run specific test file
uv run pytest rotkehlchen/tests/api/test_assets.py

# Run specific test
uv run pytest rotkehlchen/tests/api/test_assets.py::test_add_user_asset

# Filter tests with -k
uv run pytest -k add_user_asset

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

#### Attaching a devtools client to the Electron window (`DEBUGGER_PORT`)

`pnpm dev` can start Electron with Chromium's remote debugging endpoint open, so an external CDP
client (Chrome DevTools, `connectOverCDP` from Playwright or Puppeteer, an MCP devtools server) can
inspect and drive the running app. It is off unless you ask for it.

Set the port in `frontend/app/.env.development.local`, which is gitignored:

```bash
DEBUGGER_PORT=9222
```

`pnpm dev` then forwards `--remote-debugging-port=9222` to the Electron child and logs
`starting rotki with args: --remote-debugging-port=9222` at startup. Attach on
`http://127.0.0.1:9222`.

- Do not put it in `frontend/app/.env`: that file is tracked, so the value would apply to everyone.
- Electron only. `pnpm dev:web` drops the flag, because in web mode there is no Electron child to
  pass it to.
- It is not allocated per dev instance the way the dev/REST/proxy/colibri ports are, so two
  instances started with the same `DEBUGGER_PORT` collide and the second Electron comes up without
  a debugger. Give each instance its own value if you run more than one at a time. Anything outside
  13000-22995 (the instance port block) and clear of 9229 (node `--inspect`) works; 9222 is
  Chromium's own default.

The wiring, if you need to change it: `getDebuggerPort()` in
`frontend/scripts/dev/prerequisites.ts` reads the variable, `startDevServer()` in
`frontend/scripts/dev/services.ts` appends the flag, and `frontend/app/scripts/serve.ts` passes it
to the spawned Electron process.

An MCP-based assistant can reach the same endpoint through a stdio devtools server:

```json
{
  "mcpServers": {
    "electron-devtools": {
      "type": "stdio",
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--browserUrl", "http://127.0.0.1:9222"]
    }
  }
}
```

Keep that configuration outside the repository (user-level assistant settings, or an untracked
`.mcp.json` above the checkout) so it is not imposed on contributors who do not use the tool.

#### Command durations: always set an explicit timeout

The frontend gates are slow, and CI is slower than a development machine. Budget against a slow-CI
baseline (roughly 4x a fast 16-core workstation), not against your own warm-cache run. Automated
assistants must pass an explicit timeout on these commands rather than relying on a short default.

| Command | Allow at least |
|---------|----------------|
| `pnpm run lint:file <paths>`, `pnpm run lint:file:check <paths>`, `pnpm run lint-staged` | 2 minutes (usually the default) |
| `pnpm run test:unit <path>` narrowed to one file or folder | 5 minutes |
| `pnpm run lint`, `pnpm run lint:all`, `pnpm run typecheck`, `pnpm run build`, `pnpm run test:unit` (full suite), `pnpm install` | 10 minutes |
| `pnpm run test:e2e`, `pnpm run test:e2e:shards`, `pnpm run electron:build`, docker builds | run in the background instead. The unsharded e2e suite takes ~20 minutes locally and the sharded one ~7, both of which outlast any foreground timeout. |

Reference measurements (2026-08-09), so a later reader can tell whether this has drifted. The
frontend gates run as separate steps of one **"Frontend checks"** job (3m50s-5m10s including
install), so the CI column names the step rather than a whole job:

| Command | 16-core workstation, warm cache | CI (`ubuntu-latest`, 4 cores) |
|---------|---------------------------------|-----------------------------------------------|
| `pnpm run lint` | 54s (multithreaded; 159s before `--concurrency=4`) | ESLint step: 110-154s (208-226s before `--concurrency=4`) |
| `pnpm run typecheck` | 56s | Typecheck step: 59-86s |
| `pnpm run build` | | Build step (`build:app`): 12-17s |
| `pnpm run test:unit` (full) | 114s | "Frontend unit tests / vitest" job: 483-519s |
| `pnpm run lint:style` | 2s | Stylelint step: 2s |
| `pnpm run check:linked-keys` | 1s | Linked i18n keys step: 1s |
| `pnpm run test:e2e` (full, unsharded) | ~20 minutes | 240-637s per shard, across four shards |
| `pnpm run test:e2e:shards` (full, four local shards) | 7.1 minutes, 806 MB peak per shard | not used; CI shards across runners |

Runner speed varies by about 1.4x between runs, and it moves every step together, so compare a
step against its own range rather than reading one slow run as a regression.

The Typecheck and Build steps are `pull_request`-only (`github.event_name != 'push'`), so a push
straight to a branch never typechecks. ESLint, Stylelint and the i18n key check run on every event.

A command that hits its timeout has not failed, it has been cut off. Re-run it with a larger
timeout or in the background. Do not report the truncation as a result, and do not retry at the
default timeout on the assumption it was a fluke.

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
    - `modules/` - Feature modules. Each module groups its components, composables, Pinia stores, and types together (e.g. `modules/balances/`, `modules/dashboard/`, `modules/settings/`). The `modules/core/` and `modules/shell/` parents hold cross-cutting building blocks.
    - `pages/` - Route pages
    - `layouts/` - Top-level layout components
    - `locales/` - i18n translation files
    - `router/` - Route definitions
    - `plugins/` - Vue/Pinia plugin setup
  - `electron/` - Electron main process code
  - `tests/unit/` - Unit-test setup, fixtures, and mocks (specs themselves are co-located next to the source files in `src/`)
  - `tests/e2e/` - Playwright E2E specs, page objects, and helpers

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
- New composables and components go under `modules/<domain>/` (components in
  `modules/<domain>/components/`), not in a top-level `composables/` or `components/` directory.
  The codebase is organised by module, and new code follows that structure.

### Code Organization & Maintainability

- **Split complex logic**: Break down large templates and script logic into smaller, focused composables
- **Component decomposition**: Split large components into smaller, reusable sub-components
- **Logical separation**: Each composable should have a single, well-defined responsibility
- **Maintainability focus**: Prioritize code readability and maintainability over brevity

#### Lint & Warning Hygiene
- **Leave code cleaner than you found it**: When touching a file, fix any existing lint warnings in the code you modify. The goal is to steadily reduce the overall warning count over time.
- **Avoid type assertions (`as`)**: Prefer type guards, `instanceof`, `satisfies`, or discriminated unions over `as` casts. Type assertions bypass the compiler and hide bugs.
  ```typescript
  // ✅ Correct — type guard
  function isUser(value: unknown): value is User {
    return typeof value === 'object' && value !== null && 'id' in value;
  }

  // ✅ Correct — satisfies (validates shape without widening)
  const config = { timeout: 5000 } satisfies Partial<Config>;

  // ✅ Correct — discriminated union
  if (event.type === 'trade') { /* event is narrowed */ }

  // ❌ Incorrect — type assertion
  const user = response.data as User;
  const element = event.target as HTMLInputElement;
  ```
  Cast-free ways out of the usual traps: build a `new Map<string, X>(Object.entries(obj))` and use
  `.get(key)` for dynamic lookups instead of `as Record<string, X>`; use `Reflect.get(obj, key)` to
  read a dynamic field; in unit tests use `createMock<T>()` (see Testing below) instead of a double
  cast. Keep the assertions that are genuinely unavoidable, one per boundary, each with a one-line
  justification. Never launder a type through `any` to dodge the lint rule; that is worse than a
  documented `as`.
- **No barrel files**: do not create or extend `index.ts` re-export modules. The
  `@rotki/max-dependencies` rule caps a file at 20 imports, and a barrel is not the way to satisfy
  it. Reduce real imports instead (drop unused ones, or fold a genuinely cohesive group behind one
  domain composable), or leave the file as it is.
- **`max-lines` caps `.ts` files at 400 lines** (error, from `@rotki/eslint-config`; specs, `.d.ts`,
  and scripts are exempt). The cap is binding: no non-spec `.ts` file in `app/src` currently exceeds
  it. A file at the ceiling needs to be split before it can grow, so plan the split rather than
  shaving lines. **The rule does not apply to `.vue` files**, so nothing stops an SFC from growing
  without limit. See the SFC size guidance below.
- **`@rotki/composable-return-readonly`**: a composable returning a writable `Ref` must wrap it in
  `readonly()`. When the ref is intentionally writable because a consumer binds it with `v-model`,
  `readonly()` would break the binding, so **prefix the returned name with `model`** instead (for
  example `privacy` becomes `modelPrivacy`) and the rule skips it. Do not reach for
  `eslint-disable`; the existing suppressions are debt to convert, not precedent.

#### Vue.js and TypeScript Conventions
- Use VueUse utilities for reactive state management
- **IMPORTANT: Use `get()` and `set()` from VueUse instead of `.value` when working with refs**
- **Floating Promises**: Never use `void` for floating promises. Instead, use `startPromise()` from `@shared/utils`:
  ```typescript
  // ✅ Correct
  import { startPromise } from '@shared/utils';
  startPromise(someAsyncFunction());

  // ❌ Incorrect
  void someAsyncFunction();
  ```

#### Explicit TypeScript Typing Requirements

- **Always use explicit types for refs**: `ref<boolean>(false)` instead of `ref(false)`
- **Always use explicit types for computed**: `computed<boolean>(() => ...)` instead of `computed(() => ...)`
- **Always return explicit types from functions**: `function getName(): string { ... }`
- **Always type reactive variables**: `const isLoading = ref<boolean>(false)`
- **Always type computed properties**: `const fullName = computed<string>(() => ...)`
- If a ref type can be undefined and the default value is undefined, **Don't explicitly put it as type or default value**: `const newId = ref<number>()`
- **Always use `{ useScope: 'global' }` parameter for `useI18n()`**: `const { t } = useI18n({ useScope: 'global' });`
- **Never pass `t` as a parameter to a composable.** `useI18n` is auto-imported and available
  everywhere, so a composable that needs translations calls it internally. Passing `t` in is
  unnecessary coupling.
- **Use `as const` objects instead of TypeScript enums for new types**, with the type derived from
  the object. Enums are a legacy pattern here (they tree-shake poorly and infer badly). Existing
  enums stay as they are unless you are already reworking that file extensively.

#### Correct Examples:

```typescript
// ✅ Correct - Explicit typing with VueUse get/set
import { get, set } from '@vueuse/shared';

const isVisible = ref<boolean>(true);
const count = ref<number>(0);
const items = ref<string[]>([]);
const user = ref<User>();

const { t } = useI18n({ useScope: 'global' });

const isEven = computed<boolean>(() => get(count) % 2 === 0);
const formattedName = computed<string>(() => `${get(firstName)} ${get(lastName)}`);
const newId = ref<number>(); // this newId type is number | undefined.

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

const { t } = useI18n();

const isEven = computed(() => count.value % 2 === 0);
const formattedName = computed(() => `${firstName.value} ${lastName.value}`);
const newId = ref<number | undefined>(undefined);

function getUserById(id: number) {
  return users.value.find(user => user.id === id) || undefined;
}

async function fetchData() {
  return await $fetch('/api/data');
}
```

- VueUse utilities like `get()`, `set()`, `toRefs()`, `computed()` etc. are auto-imported
- Use Pinia for state management - stores live alongside their feature module as `frontend/app/src/modules/<feature>/use-*-store.ts` (e.g. `modules/balances/use-balances-store.ts`)
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

##### Props — destructured with defaults (Vue 3.5+)
- Prefer destructured props with inline defaults over `withDefaults`:
  ```typescript
  // ✅ Preferred (Vue 3.5+)
  const { title, count = 0, disabled = false } = defineProps<{
    title: string;
    count?: number;
    disabled?: boolean;
  }>();

  // ❌ Legacy — avoid in new code
  const props = withDefaults(defineProps<{
    title: string;
    count?: number;
    disabled?: boolean;
  }>(), {
    count: 0,
    disabled: false,
  });
  ```
- For mutable default values (arrays, objects), use a factory function:
  ```typescript
  const { items = () => [], filters = () => ({}) } = defineProps<{
    items?: string[];
    filters?: Record<string, string>;
  }>();
  ```
- **Reactive prop passing rules** — destructured props are reactive in `computed()`, `watch()`, and templates, but they are **not** `Ref<T>` objects. When passing to composables or watchers:
  ```typescript
  const { category, chains, address } = defineProps<{
    category: string;
    chains: string[];
    address: string;
  }>();

  // ✅ watch() — wrap in getter
  watch(() => category, (val) => { ... });

  // ✅ MaybeRefOrGetter<T> param — pass as getter
  const helper = useMyComposable(() => category);

  // ✅ MaybeRef<T> or Ref<T> param — wrap with toRef
  const data = useOtherComposable(toRef(() => chains));

  // ✅ computed() — use directly (reactive)
  const label = computed<string>(() => `${category}-${address}`);

  // ❌ Don't use toRef when a getter suffices (MaybeRefOrGetter)
  const helper = useMyComposable(toRef(() => category));

  // ❌ Don't use toRefs(props) — destructure directly
  const props = defineProps<{ ... }>();
  const { category } = toRefs(props);
  ```

##### Composable argument conventions
- When authoring composables, accept `MaybeRefOrGetter<T>` for maximum flexibility and use `toValue()` internally to normalize inputs
- `toValue()` handles plain values, refs, and getter functions uniformly
- Use `onWatcherCleanup()` (Vue 3.5+) instead of `onCleanup` callback parameter for cleaner extraction into helper functions

##### Emits — typed tuple syntax
- Use the typed tuple syntax for emit definitions:
  ```typescript
  const emit = defineEmits<{
    'update:msg': [msg: string];
    'delete': [id: number];
  }>();
  ```

##### v-model — `defineModel` (Vue 3.4+)
- Use `defineModel` for all v-model bindings instead of manual prop + emit:
  ```typescript
  // ✅ Correct — defineModel
  const modelValue = defineModel<string>({ required: true });
  const selected = defineModel<number>('selected');
  const filters = defineModel<Filters>('filters', { default: () => ({}) });

  // ❌ Incorrect — manual prop + emit for v-model
  const props = defineProps<{ modelValue: string }>();
  const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
  ```

##### Template refs — `useTemplateRef` (Vue 3.5+)
- Use `useTemplateRef` for typed template refs:
  ```typescript
  // ✅ Correct — Vue 3.5+
  import { useTemplateRef } from 'vue';
  const formRef = useTemplateRef<InstanceType<typeof MyForm>>('formRef');

  // ❌ Incorrect — old pattern
  const formRef = ref<InstanceType<typeof MyForm>>();
  ```
  ```html
  <MyForm ref="formRef" />
  ```

##### Other conventions
- Use `$attrs` in templates instead of `useAttrs`

#### Single-file component size

The median SFC in `app/src` is 75 lines and 90% are under 230. Treat **~200 lines as the point to
start splitting** and **~300 as the point where you need a reason not to**. Unlike `.ts` files,
`.vue` files are not covered by the 400-line `max-lines` rule, so nothing will stop a component from
growing without limit: this is a judgment call the linter does not make for you.

Split along the grain, not to hit a number:
- **Logic goes to a composable.** Move `<script setup>` state and behaviour into a `use-*.ts` in the
  same module folder and keep the SFC as wiring. This is the highest-value split, because a
  composable can be unit-tested directly while template logic cannot. Order what remains as described
  in "Setup Script Organization (Preferred Order)" above.
- **Template regions go to child components** under `modules/<domain>/components/`, when a region is
  independently meaningful: a row, a summary card, one step of a form.

Signals you are already past the point of splitting: the file needs more than 20 imports (the
`@rotki/max-dependencies` ceiling), `vue/max-template-depth` or `vue/max-props` starts warning,
`<script setup>` is longer than the template, or one file handles more than one concern (for example
a table plus its edit dialog plus its filters).

Do not split for its own sake. A child component used once that only forwards props adds indirection
without reducing complexity; extract the logic instead.

#### Pinia Store Structure
1. State definitions
2. Computed getters
3. Actions
4. Optional watchers

**Stores are state-only and synchronous.** No `async`/`await` actions and no API calls inside a
store. A store holds refs, computed getters, and synchronous setters (for example
`setSummary(...)`). The async fetching that writes into the store belongs in a separate composable
that calls the store's setter. For example `use-data-issues-inbox-store.ts` holds `counts` plus an
`actionableCount` getter and `setSummary()`, while `use-data-issues-summary.ts` does the async
`refreshSummary()` and calls `store.setSummary(...)`. This keeps stores predictable, testable, and
free of side effects.

#### Styling
- Use Tailwind CSS for all styling
- Scoped CSS modules (`<style module>`) should only be used for Vue `TransitionGroup` animations
- Do not use scoped SCSS with BEM naming conventions

#### Localization
- For the localization files (en.json, es.json, etc.), the keys should be ordered alphabetically.
- Avoid dynamic keys for translations, as they can break the linter.

#### Testing
- Run all tests with `pnpm run test:unit` from `frontend/` directory
- Run a single test file: `pnpm run test:unit src/modules/path/to/file.spec.ts` (no `-- --run` needed)
- Use Vitest for unit tests with Vue Test Utils
- **Unit test file naming**: `.spec.ts` files should follow the naming of the tested file and be located in the same folder
  ```
  // Example structure:
  src/modules/balances/use-balances-store.ts
  src/modules/balances/use-balances-store.spec.ts

  src/modules/accounts/use-account-import-export.ts
  src/modules/accounts/use-account-import-export.spec.ts
  ```
- **All unit tests are co-located** next to the source file they test (not in a separate `tests/` directory)
- Test descriptions must follow the `it('should ...'` pattern
- Component tests should follow existing patterns in co-located `*.spec.ts` files
- **Re-run the full `pnpm run typecheck` after editing any `.spec.ts`**, even if you typechecked
  earlier in the change. The "Frontend lint" CI job runs `pnpm run build`, and `vue-tsc --build`
  type-checks specs too, so a green `test:unit` plus a green `lint:file:check` does not prove the
  spec compiles. Type your mocks (`vi.fn<(id: number) => void>()`) so they stay assignable to the
  callback or DOM method they stand in for.
- **Narrow types with an assertion, never an `if`**: an `if (!result.ok) { expect(...) }` passes
  silently when the branch is wrong, because the body never runs. Import `assert` from `vitest`,
  assert the discriminant (which also narrows the following lines), then expect:
  ```typescript
  import { assert, describe, expect, it } from 'vitest';

  const result = await useDataIssuesApi().listIssues(payload);
  assert(!result.ok);                          // fails loudly, and narrows to the error variant
  expect(result.error.type).toBe('not-found');
  ```
- **Shared test helpers** live in `frontend/app/tests/unit/` and are imported through the `@test/*`
  alias (defined in `tsconfig.vitest.json`):
  - `createMock<T>(overrides?)` from `@test/utils/create-mock` is the generic stubber. Use it for
    branded, class, or large types where the test only reads a few fields, instead of a
    `as unknown as T` double cast. It returns a `Proxy`, so proxies do not deep-equal: build a real
    object when you need `toEqual`.
  - `mockT` from `@test/i18n` is the echo translator. `useI18n` is globally mocked in
    `tests/unit/setup-files/setup.ts` to use it, so composables calling `useI18n()` get `t` for free.
  - Other fixtures: `@test/mocks/file`, `@test/utils/create-pinia`, `@test/utils/events`.
- **Test selectors**: use `data-testid`, in components and in queries alike. `data-cy` is gone from
  the codebase; do not reintroduce it. `@rotki/ui-library` exposes no test-id attribute of its own,
  so a `data-testid` on a `Rui*` component falls through `$attrs` onto its root element.
- **e2e: never locate a row by index.** Anchoring a history-events assertion on row position makes
  the test pass for the wrong reason as soon as ordering or fixture data shifts. Anchor on fixture
  content, and pair the assertion with a negative control that proves the test can fail.

#### Fast checks via pnpm scripts

All checks are run from the `frontend/` directory through the workspace scripts — do not invoke the underlying tools directly. To avoid running everything on every iteration, prefer these script-only paths:

- **Vitest — narrow to a file or folder** (already path-aware):
  ```bash
  pnpm run test:unit src/modules/dashboard/edit-snapshot/EditSnapshotDialog.spec.ts
  pnpm run test:unit src/modules/dashboard/edit-snapshot/    # whole folder
  pnpm run test:unit:watch src/modules/<feature>/<file>.spec.ts
  ```
  Positional args are forwarded to `vitest run --coverage`. No `-- --run` separator needed.

- **Lint only what you've staged**:
  ```bash
  git add <paths>
  pnpm run lint-staged           # runs eslint on staged files; stylelint on staged .vue/.scss
  ```
  This is the canonical fast lint loop and only touches files in the git index. The same hook runs automatically on commit (via Husky), so passing it locally first means the commit won't bounce.

- **Lint specific files** (the fast path when they are not staged yet):
  ```bash
  pnpm run lint:file <paths>         # eslint --fix on those files
  pnpm run lint:file:check <paths>   # report-only, does not mutate
  ```
  Use `lint:file:check` when a fix would be destructive to inspect, for example on locale files,
  where the unused-keys autofix deletes keys.

- **Lint the whole project (full pass)**:
  ```bash
  pnpm run lint        # report-only
  pnpm run lint:fix    # auto-fix what it can
  ```

- **Never invoke the tools directly.** `pnpm exec eslint`, `pnpm exec vitest`, and `pnpm exec vue-tsc`
  run with whatever working directory you happen to be in, which silently breaks CWD-relative rule
  options and config resolution, and manufactures failures that are not real. One concrete case:
  running `eslint app/src/locales/en.json` from `frontend/app` made `@rotki/no-unused-i18n-keys`
  resolve its `src` option to a nonexistent `app/app/src`, so it reported all ~3563 keys as unused.
  The scripts pin the working directory to `frontend/`. If no script covers what you need, add one
  to `frontend/package.json` rather than reaching for `pnpm exec`.

- **Stylelint** is wired the same way: `pnpm run lint-staged` covers staged `.vue`/`.scss`; `pnpm run lint:style` does the full pass.

- **Typecheck — incremental, project-wide**:
  ```bash
  pnpm run typecheck   # vue-tsc --build --force; reuses the .tsbuildinfo cache once warmed
  ```
  `vue-tsc --build` has no per-file mode, but after the first cold run subsequent passes only re-check files affected by your change (usually a few seconds). For instant single-file feedback, rely on Volar in the IDE — it uses the same `tsconfig`.

Typical fast pre-commit loop, all from `frontend/`:

```bash
pnpm run test:unit src/modules/<feature>/<file>.spec.ts   # only your spec
git add src/modules/<feature>/<file>.ts src/modules/<feature>/<file>.spec.ts
pnpm run lint-staged                                       # only your files
pnpm run typecheck                                         # incremental
```

### Contribution guide

The contribution guide can be seen here: https://docs.rotki.com/contribution-guides/contribute-as-developer.html

### Exchange Addition

- To add an exchange you will need to add the new exchange under the `exchanges/` directory. A nice example is bitfinxex.py
- For each exchange you need to implement the basic method of the `ExchangeInterface` superclass:
  - Authentication for the api key/secret whatever the exchange API uses.
  - Fetch balances from the exchange
  - Fetch deposits/withdrawals (also called asset movements) and trades.
- You will need to create some tests with mocked data

### Adding a Frontend Setting

When adding a new setting to the frontend, follow these steps:

Settings are declared once in the **settings registry**, the single source of truth for a setting's
storage channel, value type, search row and scroll target. `SettingsItem` and the settings search both
derive from it - there is no hand-maintained search list.

#### 1. Add the highlight (anchor) id in `frontend/app/src/modules/settings/setting-highlight-ids.ts`

The **anchor** is the DOM scroll-to target for the settings search. Add one to `SettingsHighlightIds`
(keep alphabetical). Several settings may share one anchor (a *composite*, e.g. amount format).
```typescript
export const SettingsHighlightIds = {
  // ... existing entries (keep alphabetically sorted)
  MY_NEW_SETTING: 'setting-my-new-setting',
} as const;
```
If the setting needs a **new category** on its page, also add a `SettingsCategoryIds` entry.

#### 2. Register the setting in the registry

Add the key to its channel slice (`settings-registry-{general,frontend,session,accounting}.ts`). The
channel builder validates the wire key against that channel's settings type. Give it the `anchor`, and -
for a value setting that should appear in search - a `search` block (title/keywords are `msg.$t`-branded
i18n keys; `category` must be declared in `SEARCH_CATEGORIES`, see step 5):
```typescript
myNewSetting: general('myNewSetting', {
  anchor: SettingsHighlightIds.MY_NEW_SETTING,
  search: {
    category: SettingsCategoryIds.GENERAL,
    titleKey: msg.$t('my_setting.title'),
    keywords: [msg.$t('my_setting.subtitle')],
  },
}),
```
For a composite anchor (several keys, one highlight) put the `search` block on ONE representative key.

#### 3. Create the setting component

Use `SettingsOption` as a wrapper — it handles debounced updates, success/error messages, and API calls.
It accepts `setting` (backend), `frontendSetting`, or `sessionSetting` to target the right store.
```vue
<template>
  <SettingsOption setting="myNewSetting" :error-message="t('my_setting.error')">
    <template #title>{{ t('my_setting.title') }}</template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        v-model="value"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
```

#### 4. Add the setting to its category component

Wrap it in a `SettingsItem` and pass `setting-key` — the DOM id is derived from that key's registry
`anchor`, so the scroll target is single-sourced (no hardcoded `:id`):
```vue
<SettingsItem setting-key="myNewSetting">
  <template #title>{{ t('my_setting.title') }}</template>
  <template #subtitle>{{ t('my_setting.subtitle') }}</template>
  <MyNewSetting />
</SettingsItem>
```
A **composite** item (several settings under one shared anchor) passes the representative key, e.g.
`<SettingsItem setting-key="currency">`. An **action/info** row with no registry value (purge, change
password, db version) declares its `settingsActions` key instead — `<SettingsItem action-key="purgeData">`,
or `:id="anchorId('rpcNodes')"` on a bare section element that is not a `SettingsItem`. No template
restates a `SettingsHighlightIds` value.

#### 5. Settings search

Search rows are **derived**; there is no hand-maintained list. A value setting with a `search` block
(step 2) is surfaced automatically. Otherwise:
- a category new to search → add a `SEARCH_CATEGORIES` entry in `settings-search-catalog.ts` (its tab +
  header title; set `flat: true` for a page whose settings are not nested under a category heading);
- a row with no registry value (an action, an info row, or a categoryless section) → add an entry to
  `settingsActions` in `settings-actions.ts` (an `anchor` + `titleKey`/`keywords`; a `category` row nests
  under a header, a `tab` row sits on its tab), then reference it from the template with
  `action-key="<key>"` or `:id="anchorId('<key>')"`.

#### 6. If adding a new category

Create a category component wrapping `<SettingCategory>` + `<SettingsItem>`s, then in the page file
(e.g. `frontend/app/src/pages/settings/general/index.vue`) add the category id to the `navigation` array
and render the component with `:id="SettingsCategoryIds.MY_CATEGORY"`.

#### 7. Add translations

Add all labels, subtitles, and error messages to `frontend/app/src/locales/en.json` (keys must be
alphabetically sorted). A key referenced only from the registry/catalog must be branded with
`msg.$t(...)` so the unused-key lint rule counts it as used.

#### Key files reference

| Purpose | File |
|---------|------|
| Highlight (anchor) & category IDs | `frontend/app/src/modules/settings/setting-highlight-ids.ts` |
| Setting registry (source of truth) | `frontend/app/src/modules/settings/settings-registry.ts` + `settings-registry-<channel>.ts` |
| Registry builders & types | `frontend/app/src/modules/settings/settings-channels.ts` |
| Search category headers | `frontend/app/src/modules/settings/settings-search-catalog.ts` |
| Search action/info rows + `anchorId` | `frontend/app/src/modules/settings/settings-actions.ts` |
| Search deriver | `frontend/app/src/modules/settings/use-settings-search.ts` |
| Highlight/scroll logic | `frontend/app/src/modules/settings/use-settings-highlight.ts` |
| i18n key branding helper | `frontend/app/src/message-key.ts` (`msg.$t`) |
| Setting update wrapper | `frontend/app/src/modules/settings/controls/SettingsOption.vue` |
| Setting layout wrapper (`setting-key`/`action-key` → id) | `frontend/app/src/modules/settings/controls/SettingsItem.vue` |
| Category visual grouping | `frontend/app/src/modules/settings/SettingCategory.vue` |
| Settings pages | `frontend/app/src/pages/settings/*/index.vue` |

### Adding EVM protocol decoders

As an example decoder, we can look at [MakerDAO](https://github.com/rotki/rotki/blob/1039e04304cc034a57060757a1a8ae88b3c51806/rotkehlchen/chain/ethereum/modules/makerdao/decoder.py).

It needs to contain a class that inherits from the `DecoderInterface` and is named `ModulenameDecoder`.

Note: If your new decoder decodes an airdrop's claiming event and this airdrop is present in the [data repo airdrop index](https://github.com/rotki/data/blob/develop/airdrops/index_v2.json) with `has_decoder` as `false`, please update that also.

When you need to check a contract ABI, use Sourcify's repository URL format:
`https://repo.sourcify.dev/<chainID>/<contract_address>`.
For example, for address `0x3337286E850cf01B8A8B6094574f0dd6a2108B16` on chain ID `1`, check `https://repo.sourcify.dev/1/0x3337286E850cf01B8A8B6094574f0dd6a2108B16`.
For raw ABI data, read the verified metadata JSON at `https://repo.sourcify.dev/contracts/full_match/<chainID>/<contract_address>/metadata.json` and use `output.abi`.

### Decoder scope policy (performance-critical)

- Prefer `addresses_to_decoders()` over generic `decoding_rules()` whenever a protocol emits identifiable logs from known contract addresses.
- Use `decoding_rules()` only as a last resort when no reliable address/topic/input selector scoping exists.

Why:
- `decoding_rules()` are evaluated for every log in every transaction on that chain, which increases per-log decoding overhead.
- `addresses_to_decoders()` restricts execution to logs from relevant protocol contracts, reducing unnecessary rule invocations and improving decode throughput.
- Narrow-scoped decoders also reduce false positives and make behavior easier to reason about.

### ActionItem matching rule (avoid redundant log scans)

- When creating an `ActionItem` from a log handler, prefer using data already available in the current `context.tx_log` for matching fields (`amount`, `asset`, `location_label`, `to_address`) whenever possible.
- Do not iterate `context.all_logs` just to rediscover transfer data if the current log already provides the same amount/address relation.
- Only scan `context.all_logs` when correlating multiple distinct logs is strictly required.

Why:
- Reduces per-transaction work and decoder complexity.
- Avoids introducing fragile cross-log assumptions.
- Keeps action-item transformations deterministic and easier to review.

### Fallback when chain indexers are unavailable

If a chain cannot be queried via explorer/indexer APIs (`etherscanscan` / `routescan` / `blockscout` etc ), do not stop. Use this fallback flow:

1. Add a public RPC node for the chain in the test via `*_manager_connect_at_start` + `WeightedNode(NodeName(...))`.
2. Query tx/receipt/logs from RPC directly (not from explorer APIs).
3. If internal txs are not needed for the specific decoder path, patch:
   `rotkehlchen.chain.evm.transactions.EvmTransactions._query_and_save_internal_transactions_for_range_or_parent_hash`
   to return `[]`.
4. Keep the test focused on decoded events from logs/transfers.
5. Prefer deterministic assertions and exact tx-hash regression tests.
6. Do not block on explorer availability; only ask the user if RPC data is insufficient.

Example intent: Base currently may fail on explorer/indexer paths; use `https://mainnet.base.org` until indexers recover.

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

### Hex / bytes constants policy (strict)

- Source of truth: copy exact on-chain/API `0x...` hex.
- Validation step (during implementation): convert with `bytes.fromhex(hex_str.removeprefix('0x'))` and verify round-trip:
  - `hex_str = value.removeprefix('0x')`
  - `const = bytes.fromhex(hex_str)`
  - `assert const.hex() == hex_str.lower()`
- Final committed form: all event topics, method selectors, hashes, and byte signatures must be byte literals (for example `TOPIC: Final = b'\xdc\xbc\x1c\x05...\xd7'`).
- Do not keep `bytes.fromhex(...)` in final constant definitions.
- If useful for readability, keep the canonical `0x...` value as a comment next to the byte literal.
- Don't put assets as constants. If you need a constant just use the asset identifier as a string and compare against it.

### Database schema changes (user DB and global DB)

rotki has two SQLite databases that each carry a version and an ordered list of upgrade scripts: the **user DB** and the **global DB**. The same rule applies to both — when you need a schema change (add/alter a table, add a settings row, backfill data) **do not blindly create a new upgrade and bump the version**. First check whether the latest existing upgrade has already been released:

1. Find the highest `vN_vN+1.py` upgrade (the one matching the current version constant — see the per-DB table below).
2. Check whether that upgrade is **already released**. Read its docstring (it says e.g. "This happened in 1.44" / "This upgrade takes place in v1.44.0") and compare against the latest released rotki version (`docs/changelog.rst` / git tags).
3. **If the latest upgrade is already released** → create a new `vN_vN+1.py`, bump the version constant, register it in the upgrades list, add a test, and (global DB only) extend the `Literal` in `tests/utils/globaldb.py::patch_for_globaldb_upgrade_to`.
4. **If the latest upgrade is still unreleased** (same upcoming version as your change) → **add your step to that existing upgrade instead** of creating a new one. Do NOT bump the version and do NOT add a new upgrade file. Add an assertion for your change to that upgrade's existing test rather than a separate test.

Per-DB locations:

| | User DB | Global DB |
|---|---|---|
| Version constant | `ROTKEHLCHEN_DB_VERSION` in `rotkehlchen/db/settings.py` | `GLOBAL_DB_VERSION` in `rotkehlchen/globaldb/utils.py` |
| Upgrade scripts | `rotkehlchen/db/upgrades/vN_vN+1.py` | `rotkehlchen/globaldb/upgrades/vN_vN+1.py` |
| Upgrades list | `UPGRADES_LIST` in `rotkehlchen/db/upgrade_manager.py` | `UPGRADES_LIST` in `rotkehlchen/globaldb/upgrades/manager.py` |
| Fresh-create schema | `rotkehlchen/db/schema.py` | `rotkehlchen/globaldb/schema.py` |

Always keep the fresh-create schema (`schema.py`) in sync with the upgrade so newly created DBs match the upgraded state.

**Global DB only — extra hazard:** the global DB also ships as a packaged file (`rotkehlchen/data/global.db`) in the `rotki/data` submodule, which is only regenerated/bumped per release. Bumping `GLOBAL_DB_VERSION` ahead of that packaged DB makes its version (e.g. 17) mismatch the code (e.g. 18), which breaks `soft_reset_assets_list`/`hard_reset_assets_list` (version-equality guard) and the packaged-DB consistency tests — exactly the kind of "tests fail on develop" caused by an unmerged data-repo change. This is the strongest reason to fold into the unreleased upgrade rather than create a premature new version.

## Rotki Backend Style Preferences (strict)

When editing backend Python and tests, follow these preferences unless explicitly told otherwise:

1. Prefer narrow exceptions.
 - Do not use `except Exception`.
 - Catch the concrete error type used by the surrounding code path (e.g. `RemoteError` for rpc/multicall).

 2. Prefer inline one-time assignment via walrus operator.
 - If a variable is used only once in a small local scope, inline it with `:=` instead of introducing a standalone line.
 - Apply this especially in tests for constants like `timestamp`, `amount_str`, `gas_str`, `user_address`.
 - Example: `location_label=(user_address := ethereum_accounts[0])`.

 3. Avoid unnecessary temporary locals.
 - If a value is only used once and readability is preserved, inline it.
 - Keep code compact and avoid “setup variable blocks” in tests.

 4. Keep existing codebase idioms first.
 - Match nearby file style even if generic Python style differs.
 - For rotki tests, prefer concise expected-event construction with inline assignments where practical.

## Testing Strategy

### Historical balance / accounting refactor context

When a user mentions the "accounting refactor", "accounting buckets", "balance buckets", or issue/PR `#12204`, assume they are referring to the historical balance engine in `rotkehlchen/tasks/historical_balances.py` and its `event_metrics` bucket tracking, not the legacy accounting pot/cost-basis code unless they explicitly say cost basis or PnL accounting.

Key files:
- `rotkehlchen/tasks/historical_balances.py` — bucket derivation and event metric generation.
- `rotkehlchen/balances/historical.py` — historical balance query/read API.
- `rotkehlchen/db/schema.py` — `event_metrics` schema.
- `rotkehlchen/db/history_events.py` — stale marker invalidation when events change.
- `rotkehlchen/tests/unit/test_historical_balances.py` and `rotkehlchen/tests/api/test_historical_balances.py` — primary tests.

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
- **Unit tests are co-located**: `.spec.ts` files live next to the source file they test in `frontend/app/src/`
- Test utilities (fixtures, mocks, setup) remain in `frontend/app/tests/unit/`
- Playwright for E2E testing (specs in `frontend/app/tests/e2e/specs/`, page objects in `frontend/app/tests/e2e/pages/`, helpers in `frontend/app/tests/e2e/helpers/`)
- Test descriptions must follow the `it('should ...'` pattern

#### Running e2e locally, sharded

The backend is single-user, so one Playwright run is pinned to `workers: 1` and takes about
twenty minutes. `pnpm run test:e2e:shards` starts several complete stacks side by side instead -
each with its own starling supervisor, rpc mock, preview server, port block and data directory -
and gives each one a shard of the suite. The whole suite takes about seven minutes across four
shards, at roughly 800 MB peak per shard.

```bash
cd frontend
pnpm run test:e2e:shards                                              # four shards
pnpm run test:e2e:shards -n 2                                         # two
pnpm run test:e2e:shards -n 2 tests/e2e/specs/app/tag-manager.spec.ts # only these specs
pnpm run test:e2e:shards -n 2 -- --grep @slow                         # raw playwright flags
```

Spec paths are positional, so no `--` is needed for them; pnpm forwards arguments verbatim.
A `--` separates flags meant for Playwright rather than for the runner.

Useful to know:
- Shard N takes the port block at offset `N * 10`, so the base block stays free and a plain
  `pnpm test:e2e` can run alongside a sharded one.
- Every shard is served the same bundle, built once with an empty `VITE_BACKEND_URL` so it
  addresses the backend same-origin; each preview server proxies `/api/`, `/ws/` and `/colibri/`
  to its own shard's starling. Those proxy keys are anchored regexes on purpose: a bare `/api`
  also matches the `/api-<hash>.js` chunk and the app renders a blank page.
- Each shard starts from a pristine copy of the packaged global database, so manual prices and
  other global-database residue cannot leak between runs.
- Per-shard output lands in `.e2e/shard-N/logs/shard.log`; the terminal only gets summary and
  failure lines unless `--verbose` is passed. The blob reports are merged into one
  `playwright-report` at the end.

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
1. Run backend tests directly with `uv run pytest`
2. Frontend uses strict TypeScript - ensure types are properly defined
3. Follow existing code patterns - the codebase has established conventions
4. Use the existing test infrastructure - comprehensive fixtures are available
5. WebSocket messages follow specific format - check `api/websockets/typedefs.py`
6. For all python backend constants make sure to use the `Final` type specifier.
7. Never iterate over `cursor.execute(...).fetchall()`. `fetchall()` already walks the cursor and materializes every row into a list, so a following `for` loop iterates the data a second time. When you only need a single pass, iterate the cursor directly: `for row in cursor.execute(...):`. Reserve `fetchall()` for when you genuinely need the materialized list (e.g. to reuse it, get its length, or assert on it in a test). The same applies to a write cursor — prefer a read cursor (`self.conn.read_ctx()`) for plain `SELECT`s.

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
- Backend test failures: Re-run the relevant test directly with `uv run pytest`
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
