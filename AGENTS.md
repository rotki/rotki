# AGENTS.md

Rotki is a privacy-focused portfolio and tax application. The Python backend lives in
`rotkehlchen/`, the Vue/TypeScript workspace in `frontend/`, and the Rust service in `colibri/`.
See the [contribution guide](https://docs.rotki.com/contribution-guides/contribute-as-developer.html)
for general setup and contributor help.

Backend map: `api/` (REST and WebSocket), `chain/` (blockchain integrations and decoders),
`exchanges/`, `accounting/`, `db/` (user DB), `globaldb/` (assets DB), `history/` (history events,
the core abstraction for all activity), and `externalapis/`.

## Commands and validation

Use free-threaded Python 3.14 and `uv` for the backend, and the toolchain pinned in
[`rust-toolchain.toml`](rust-toolchain.toml) for Colibri. For the frontend, use the Node version in
[`frontend/.nvmrc`](frontend/.nvmrc) and the pnpm version in
[`frontend/package.json`](frontend/package.json).

### Backend and Colibri

| Task | Command |
| --- | --- |
| Sync the backend environment from the repo root | `uv sync --python 3.14t` |
| Run pytest (add a path, `path::test_name`, or `-k expression` to narrow it) | `uv run pytest` |
| Lint / format Python | `uv run make lint` / `uv run make format` |
| Start the backend by itself | `uv run python -m rotkehlchen --api-port 4242 --websockets-port 4333` |
| Build Colibri from the repo root | `cargo build --manifest-path colibri/Cargo.toml` |

To run Colibri by itself, use `cargo run --manifest-path colibri/Cargo.toml -- --data-directory <dir> --port 4343`.
The data directory must contain `global/global.db`; the normal frontend dev command starts Colibri for you.

### Frontend

**Run all frontend commands from `frontend/`, not the repository root or `frontend/app/`.** Use the
workspace scripts, not direct `pnpm exec eslint`, `vitest`, or `vue-tsc` invocations. Some lint
rules resolve paths relative to the workspace. Add a workspace script if one is missing.

| Task | Command | Minimum timeout |
| --- | --- | --- |
| Install | `pnpm install --frozen-lockfile` | 10 min |
| Start the app and companion services | `pnpm dev` (Electron) or `pnpm dev:web` (browser) | Background |
| Check changed files without mutating them | `pnpm run lint:file:check <paths>` | 2 min |
| Fix specific files / lint staged changes | `pnpm run lint:file <paths>` / `pnpm run lint-staged` | 2 min |
| Run a unit spec or directory | `pnpm run test:unit <path>` (no `--` before the path) | 5 min |
| Run the full unit suite | `pnpm run test:unit` | 10 min |
| Run full lint checks | `pnpm run lint` (ESLint) or `pnpm run lint:all` (also checks styles and linked i18n keys) | 10 min |
| Build / typecheck | `pnpm run build` (includes typecheck) / `pnpm run typecheck` | 10 min |
| Lint, build and unit tests in one go | `pnpm run check` | 20 min |
| Run Playwright | `pnpm run test:e2e:shards` or `pnpm run test:e2e` | Background |
| Recover a broken frontend build | `pnpm run clean:modules`, then `pnpm install --frozen-lockfile` | 10 min |

- Set explicit timeouts and run long commands (E2E, packaging, Docker) in the background. A
  timed-out check is incomplete, not passed.
- Prefer report-only lint while iterating; locale autofixes can delete keys.
- **After changing any `.spec.ts`, run the full `pnpm run typecheck`**: Vitest does not typecheck.
- Run `pnpm run lint:style` and `pnpm run check:linked-keys` if you did not run `lint:all`. Run
  `pnpm run knip` before pushing; lint does not run it. Dev-proxy changes need
  `pnpm run test:proxy`.
- **Changed-file checks miss cross-file effects.** `lint-staged` lints only what is staged, so
  unstaged edits go unchecked; use `lint:file:check` on the changed files. A check that ends in a
  second or reports "no files found" did not run. Removing an export, locale key or dependency
  needs the full `pnpm run lint`, `knip` and `test:unit`.
- Removing a dependency: also update `app/scripts/chunk-groups.ts`, which no gate checks. Don't
  remove one just because knip flags it; some are resolved by name at runtime (the i18n lint rule
  loads `@typescript-eslint/parser` this way and silently finds zero keys without it).
- The slop rules inspect only what changed since `HEAD~1`, so older slop is never reported. Fix
  what they report; an `eslint-disable` for them turns into an unused-directive error once the line
  ages out. To sweep older slop, set `slop: { inspection: { mode: 'full' } }` in
  `frontend/eslint.config.js` temporarily and lint; don't commit that change.
- A "JavaScript heap out of memory" under a memory-limited cgroup usually means the limit, not the
  code: Node sizes its heap from it, and typecheck needs more than 2 GB.

### Before handoff

- Execute the exact tests added or changed and the relevant surrounding file or focused suite. For
  cross-cutting changes, cover each directly affected module. Run the required lint, typecheck, and
  formatting checks for the changed files or subsystem. Collection alone is not a test run.
- If a required check cannot run, report the change as blocked with the exact command and reason.
  Don't commit, export, or hand off a change with unrun tests unless the user explicitly accepts
  the limitation. A requested source export for cassette recording is an interim handoff: mark the
  test pending, then replay it and fix any mismatch once the recording is available.
- Report the exact validation commands and their pass/fail counts. Do not infer a passing test from
  source inspection, lint, or manually inspected transaction data.

### Electron debugging and E2E

- To enable local CDP for Electron, set `DEBUGGER_PORT=9222` in the ignored
  `frontend/app/.env.development.local` (not the tracked `.env`), run `pnpm dev`, and attach at
  `http://127.0.0.1:9222`. Pick a free port per instance, below the instance block at 13000 and away
  from 9229. Keep MCP client configuration outside the repo.
- The backend is single-user, so unsharded E2E uses one Playwright worker. The sharded runner starts
  isolated stacks and defaults to four shards. Use `pnpm run test:e2e:shards -n 2 <spec-path>` for a
  subset; use `-- --grep <pattern>` to forward Playwright flags. Logs are in
  `frontend/app/.e2e/shard-N/logs/shard.log`; reports merge into `playwright-report` under `frontend/app/`.
- If changing the E2E runner, keep shard data directories and ports isolated, start from a pristine
  packaged DB, and anchor preview proxy rules (`/api/`, `/ws/`, `/colibri/`) so they do not catch
  hashed frontend chunks such as `/api-<hash>.js`.

### Checking frontend work in the running app

Unit tests and gates do not prove a UI change. Check behavior, layout and failure paths in the app.

- Start with `pnpm run dev:web --instance <name> --no-seed` and read the ports from its log.
  Without `--instance` it uses the shared default data dir, which holds real profiles. Tear down
  with `pnpm run dev:web --clean <name> --yes`. Dev startup runs `uv sync --locked`, which drops the
  `lint` group; restore it with `uv sync --python 3.14t --group lint`.
- After creating a test user, log in through the app, not only on the backend port, or Colibri has
  no user DB and asset lookups fail. Accounting-update features need `ROTKI_ACCOUNTING_UPDATE=True`
  in the environment: it gates the backend endpoints, the Vite flag, and the backend tests
  (skipped without it).
- Fake responses by patching `window.fetch` in the page, never by writing Pinia stores: that skips
  login, task polling, schema parsing and the failure path. An async query needs three fakes: the
  call returns `{task_id}`, `GET /tasks` lists it, and `GET /tasks/<id>` returns the outcome.
- Before blaming the code: dev builds persist Pinia stores to `sessionStorage` (clear
  `pinia.store.<id>`), only one tab can be active, and Vite can serve a stale module after rapid
  edits (fetch the module URL to check).
- Changes to accounts, balances or the task orchestrator are accepted only after a log out and log
  in. Measure layout at desktop width with `getBoundingClientRect`; happy-dom cannot.

## Frontend development

### Layout and design

- Put application code under `frontend/app/src/`. Co-locate feature composables, types, and
  `use-*-store.ts` files in `modules/<domain>/`; put new components in that module's `components/`
  directory. Use `modules/core/` and `modules/shell/` for their respective cross-cutting concerns.
  Route pages live in `pages/`, Electron main-process code in `frontend/app/electron/`.
- **Pinia stores are synchronous and state-only.** Order state, computed getters, actions, then
  optional watchers. Fetch in a separate composable and write via a store action; don't put async
  actions or API calls inside stores.
- **No barrel files.** Don't create or extend `index.ts` re-export modules to work around the
  `@rotki/max-dependencies` limit of 20. Reduce real dependencies or split along feature boundaries.
- **Check the 400-line `.ts` limit before adding code.** Specs, declarations, and scripts are exempt.
  Split a file at the limit rather than trimming documentation to fit. For `.vue` files, start
  looking for seams around 200 lines and have a reason not to split around 300. Extract behavior
  into a local composable first; extract template regions with a responsibility of their own, not
  wrappers that just forward props. For a risky split, first commit specs that pin the current
  behavior (each checked with a negative control), then split without editing them. Keep global
  side effects (key handlers, route guards, `provide`) where they are.
- Fix lint warnings in the code you touch. Use Tailwind for styling; reserve scoped CSS modules for
  `TransitionGroup` animations and avoid scoped SCSS with BEM names. Keep locale keys alphabetized
  and avoid dynamic translation keys.

### Behavior rules

- A watcher, listener or poller that reacts to shared state belongs in a shared composable or at
  app init. In a composable many components call, it registers once per caller (one setting change
  once sent 32 identical requests).
- Failures must reach the user; silence is a decision, not a default. Use `isRequestCancellation`
  for the user's own cancels. A test of an error path asserts the message content, not only that a
  notify call happened.
- Keep the request queue's `maxConcurrent` at 6 (the browser's per-host limit). Advisory per-render
  lookups (ENS, address names) go at low priority with a timeout. `dedupe` merges only concurrent
  duplicates; cache repeats in the composable.
- Forms use `useForm`/`useModelForm` from `modules/core/form/` over zod; don't add a form library.
  Backend messages go through `setServerErrors`, never a schema rule. In the history event forms, a
  field the form only carries uses `carriedThrough()` (`event-field-schemas.ts`). Form specs
  assert through the exposed `validate()`.
- Show feedback inline where the action happened. Use a modal only when there is nowhere else to
  render it. Keep defensive disables in the UI even when the internals are correct.
- **A `@rotki/ui-library` problem is fixed in the library, not worked around here.** Fix it in
  [rotki/ui-library](https://github.com/rotki/ui-library), check it in this app against a local
  build, publish a release, and bump it here. No class overrides, `!` utilities, wrapper components
  or local patches to compensate. The package is in `minimumReleaseAgeExclude`, so a same-day bump
  works. If you cannot publish, open the library PR and stop until a maintainer releases it.
- Keep the visible focus ring (it is the outline, so no `outline-0` or `outline-hidden`). A button
  with a hidden label needs an `aria-label`. Put tables in `modules/core/table/TableFrame.vue`, not
  a `RuiCard`. Fonts and assets are self-hosted because the app must work offline.
- The premium bundle lives in another repo and uses app components (for example `AssetSelect`) and
  `en.json` keys, and no typecheck covers that boundary. When renaming a prop it uses, let the old
  attribute fall through `$attrs`. A new key the bundle reads needs an `i18n.te()` fallback.

### Vue and TypeScript conventions

- Use VueUse `get()` and `set()` instead of `.value`. Give `ref<T>()`, `computed<T>()`, and functions
  explicit types; use `ref<T>()` with no argument for an initially undefined ref.
- Prefer guards, `instanceof`, `satisfies`, or discriminated unions over `as`. For dynamic lookup,
  consider a typed `Map`. Use one justified assertion at an unavoidable boundary; never go through
  `any` to bypass lint. For new enum-like types use an `as const` object and a derived union;
  leave existing enums alone unless you are already reworking that file.
- Nothing is auto-imported: import Vue, VueUse, Pinia, vue-router and vue-i18n APIs explicitly
  (`get`/`set` from `@vueuse/shared`), and every `Rui*` component a template uses from
  `@rotki/ui-library`, merged into one import with any types from it. Import the debounce
  and throttle helpers from `@/modules/core/common/async/scoped-timers`, not `@vueuse/core`.
- Use `startPromise()` from `@shared/utils` for intentionally unawaited promises, not `void`.
- Call `useI18n({ useScope: 'global' })` where translations are needed; don't pass `t` into a composable.
- Destructure props with inline defaults (factories for arrays/objects). For composable inputs prefer
  `MaybeRefOrGetter<T>` and normalize with `toValue()`. Pass a destructured prop as a getter to a
  watcher or `MaybeRefOrGetter<T>` input; use `toRef(() => prop)` if the consumer requires a ref.
  Use `onWatcherCleanup()` rather than the watcher callback's cleanup parameter.

  ```typescript
  const { category, chains } = defineProps<{ category: string; chains: string[] }>();
  watch(() => category, ...);              // ✅ getter
  useMyComposable(() => category);         // ✅ MaybeRefOrGetter input
  useOtherComposable(toRef(() => chains)); // ✅ only when the consumer requires a Ref
  useMyComposable(toRef(() => category));  // ❌ toRef where a getter suffices
  const { category } = toRefs(props);      // ❌ destructure the props directly instead
  ```
- Use typed tuples for `defineEmits`, `defineModel` for `v-model`, `useTemplateRef` for template refs,
  and `$attrs` in templates instead of `useAttrs`.
- Return composable refs as read-only. If a ref must be writable for `v-model`, give the returned
  name a `model` prefix (e.g. `modelPrivacy`) rather than suppressing the lint rule.
- Preferred setup order: imports → Vue macros → i18n/router → state → stores → composables →
  computed → methods → watchers → lifecycle hooks → exposed methods.

### Comments and TSDoc

Enforce an invariant with a type, lint rule, test, name or helper first. If prose is still needed,
document the invariant and the trap on the declaration, never the implementation or PR history.
Move repeated call-site notes to the shared helper. Name the actual fact rather than re-deriving it
from an unrelated value.

TSDoc: a summary, optional `@remarks`, and `@param`/`@returns` only where they explain units,
sentinels or absent values. Document all parameters or none (use `@remarks` for one). No tags that
repeat the name and type (`@param chain - the chain` is worse than no tag), and no `void` return
docs.

A `//` explaining code is a last resort. One stranded mid-function (especially in a watcher) means
the block wants extracting into a named, documented function. Never shorten a comment just to
satisfy lint. `pnpm run audit:comments` lists candidates for review.

### Frontend tests

- Co-locate `.spec.ts` files with the source they test. Shared Vitest/Vue Test Utils fixtures,
  mocks, and setup live in `frontend/app/tests/unit/` and are imported via `@test/*`. Playwright specs,
  page objects, and helpers live in `frontend/app/tests/e2e/`.
- **Component tests are not optional.** `.vue` coverage lags far behind `.ts`; the remaining gap
  is logic inside SFCs. Put the component's contract in the `describe`/`it` titles, not in a header
  comment.
- **Test components with behavior.** Extract complex logic into a composable and test it directly,
  then test the SFC's public wiring: rendering given props, event payloads, dependency calls, and
  enabled/disabled states. Avoid `wrapper.vm` internals, child class lists, and mount-only tests.
  Pure display wrappers need no dedicated test. Name the behavior in `it('should ...')`.
- Use scoped, kebab-case `data-testid` selectors (e.g. `service-key-api-key`), not DOM paths or BEM.
  `@rotki/ui-library` has no test-id prop; a `data-testid` on a `Rui*` component falls through
  `$attrs` onto its root element.
  In E2E, locate rows by fixture content, not index; a virtualized DOM row count is not a data count.
- The shared setup unmounts `mount`/`shallowMount` wrappers; clean up manual `createApp` mounts
  yourself. Stub teleporting overlays with a slot pass-through when testing content. Stub layout
  measurements in happy-dom and verify real layout behavior in the browser.
- Type mocks from real dependencies (`ReturnType<typeof useX>` or `vi.fn<(id: number) => void>()`).
  When a `vi.mock` factory needs runtime imports, use `await import()` inside an async `vi.hoisted`
  callback or async factory, not `require`. Use Vitest `assert()` to narrow before expectations;
  don't put assertions behind an `if` that can silently skip them.

  ```typescript
  // ✅ vi.hoisted runs before the file's imports, so import runtime values inside it
  const { count } = await vi.hoisted(async () => {
    const { ref } = await import('vue');
    return { count: ref<number>(0) };
  });
  // ❌ const { ref } = require('vue'); // with an eslint-disable for no-require-imports
  ```
- **A passing spec prints nothing.** A `[Vue warn]`, MSW warning or stack trace in a passing run's
  stderr is a defect. Fix it in the change that introduces it, or when you touch that spec, because
  nobody else will. "Lifecycle injection APIs can only be used during execution of setup()" means a
  composable ran outside a component and its hooks never fired: wrap it with `withSetup()` from
  `@test/utils/with-setup`. For an expected `console.error`, use `captureConsoleError()` and assert
  on the spy; never silence output without asserting.
- Use `createMock<T>()` from `@test/utils/create-mock` for large or branded types. Its proxy returns
  truthy stubs for omitted properties: set every boolean the code reads and use a real object for
  deep equality. `useI18n()` is already mocked with the `@test/i18n` echo translator.
- **Verify new or changed behavior tests with a negative control.** Break the specific line (revert
  the fix or invert its guard), confirm the intended tests and only those fail, then restore. A
  control that still passes means the test cannot fail; re-aim it. Be wary of "not called" and
  "nothing emitted" checks: an exception thrown mid-handler also satisfies them.

### Settings and navigation

The settings registry is the source of truth for the storage channel, value, search, and scroll
anchor. Files below are relative to `frontend/app/src/modules/settings/` unless noted.

1. Add an alphabetized `SettingsHighlightIds` anchor in `setting-highlight-ids.ts` and register the
   key in the right `settings-registry-{general,frontend,session,accounting}.ts` slice. Add a
   `search` block for searchable values, with `msg.$t(...)` keys. Use one representative key for
   a composite's shared anchor and search entry.
2. Render the value with a typed control from `controls/` (`SettingSwitch`, `SettingNumber`,
   `SettingText`, `SettingSelect`, `SettingMultiSelect`, `SettingToggleNumber`); each takes a
   registry `setting` key and persists through `useSettingModel` with save/error feedback. Wrap the row with `SettingsItem setting-key="..."` so the DOM id comes from the registry.
   Do not duplicate the anchor in the template.
3. Put action/info rows with no registry value in `settings-actions.ts`. Use `action-key` on
   `SettingsItem`, or `anchorId(key)` on a bare section. Add new search categories to
   `SEARCH_CATEGORIES` in `settings-search-catalog.ts`; use `flat: true` for non-nested pages.
4. For a new on-page category, add a `SettingsCategoryIds` entry, a `SettingCategory` component,
   and its id in the page's `navigation` array and on the rendered section. Add translations to
   `frontend/app/src/locales/en.json`; brand registry/catalog-only keys with `msg.$t(...)`.

Routes are file-based. Navigate by the generated typed name (e.g. `'/balances/blockchain/'`);
never override `name`. Declare `definePage({ meta: { nav: ... } })` for the drawer, search, and tabs.
The shape is in [`types/router.d.ts`](frontend/app/src/types/router.d.ts).

```ts
definePage({ meta: { nav: {
  labelKey: msg.$t('navigation_menu.balances_sub.blockchain_balances'), icon: 'lu-blockchain',
  parent: '/balances/', order: 10, drawer: 'balances-blockchain',
} } });
```

- Set `labelKey` and `icon`. Set `drawer` to show an entry in the drawer (also its `data-key`
  selector). Root entries need `section` and `order`; children need `parent` and `order`. The
  parent must have `nav`; its label is the search breadcrumb.
- Routes with `nav` are searchable by default, even without a drawer entry. Use `searchable: false`
  to opt out and `keywords` for translated aliases.
- Use `useChildNavTabs(parent)` for all children of a parent or `useNavTabs(names)` for an ordered
  subset. Settings tab metadata also comes from `nav`; per-setting search comes from the registry.

Key files: `settings-channels.ts` (registry builders/types), `use-settings-search.ts` (search
deriver), `use-settings-highlight.ts` (scroll/highlight), `controls/SettingsItem.vue`,
`SettingCategory.vue`, `frontend/app/src/message-key.ts` (`msg.$t`); for navigation,
`modules/shell/layout/use-navigation-menu.ts`, `use-route-search.ts`, `use-nav-tabs.ts`, and
`modules/shell/components/GlobalSearch.vue`.

### Frontend dependency upgrades

- pnpm enforces a 7-day `minimumReleaseAge`. A `--config` override does not survive the next
  install; the only same-day route is a `minimumReleaseAgeExclude` entry. The Renovate dashboard
  can lag the registry by a week, so check npm for the newest eligible version.
- Keep the root `preinstall` script dependency-free: pnpm runs it before installing anything.
- Held versions are `allowedVersions` rules in [`.github/renovate.json5`](.github/renovate.json5),
  each with the symptom that caused it. Add one when you hold a version back, and reproduce the
  symptom before lifting it. A Node OOM or hang right after a bump is often the new version.
- The app targets the Vite default browser baseline, so avoid ES2025 APIs (iterator helpers such
  as `.take()`) in `app/src/`.

## Backend development

- Follow nearby idioms. Catch specific exceptions, not `Exception`. Avoid unnecessary temporaries;
  use a walrus for a small inline assignment when it improves readability, especially in expected
  test events. Annotate constants with `Final`.
- For a single pass, iterate `cursor.execute(...)` directly. Use `fetchall()` only when you need the
  materialized rows. Prefer read cursors for plain `SELECT`s.
- Use shared pytest fixtures in `rotkehlchen/tests/fixtures/`. For WebSocket payload shapes, see
  `rotkehlchen/api/websockets/typedefs.py`.
- For a new exchange, follow [`bitfinex.py`](rotkehlchen/exchanges/bitfinex.py) and the
  `ExchangeInterface` contract for authentication, balances, trades, and asset movements. Test with
  mocked data or the VCR workflow below as appropriate.

### Backend HTTP/RPC tests and VCR

- Any test whose external HTTP or RPC traffic can be captured by the project's VCR infrastructure
  must use `@pytest.mark.vcr`. Do not omit it because a cassette is missing or the endpoint works
  live. Mock external dependencies where a network request is not needed for the behavior under test.
- The human developer records and commits new cassettes unless they explicitly ask the assistant to
  do it. Give the exact recording command with the test node ID:
  `RECORD_CASSETTES=true uv run pytest -m vcr path/to/test_file.py::test_name`. Replay without that
  variable after recording. In review, check that the marker has a matching cassette PR in
  `rotki/test-caching`; a live run is not evidence of cassette coverage.
- For manual Etherscan queries, use v2 (`https://api.etherscan.io/v2/api` with `chainid`) and the
  `ETHERSCAN_API_KEY` environment variable. Ask for the key only if the query is needed and it is
  not set.

### EVM decoders

- Follow a current decoder such as [`MakerdaoDecoder`](rotkehlchen/chain/ethereum/modules/makerdao/decoder.py).
  Extend `EvmDecoderInterface` or its protocol-specific base, name the class `ModulenameDecoder`,
  and implement `counterparties()` with identifiers defined in `constants.py`.
- Prefer `addresses_to_decoders()` for identifiable contracts. Use broad `decoding_rules()` only
  when address/topic/input selector scoping is unavailable: they run for every log of every
  transaction on the chain. `enricher_rules()` post-process already decoded events to add
  information this module can decode. When building an `ActionItem`, match
  using fields available in `context.tx_log`; scan `context.all_logs` only to correlate distinct logs.
- Use the event helpers in `rotkehlchen/chain/evm/decoding/base.py` for location, timestamp conversion,
  and sequence indexes. `EvmEvent` stores `amount` and the transaction hash as `tx_ref`; its default
  group identifier includes the chain ID. Use `make_event_from_transaction()` at most once per log
  to avoid duplicate indexes. Timestamps are in milliseconds and `location_label` is the
  initiator. The event type/subtype/counterparty combination determines how an event is shown in
  the UI and treated in accounting; check `rotkehlchen/accounting/constants.py` for classifications.
- Verify address literals with `to_checksum_address()`. `string_to_evm_address()` is typing-only;
  it does not checksum or validate a string. Copy exact on-chain hex for topics, selectors, hashes,
  and signatures; validate with `bytes.fromhex(value.removeprefix('0x')).hex() == value.removeprefix('0x').lower()`.
  Keep byte literals, not `bytes.fromhex(...)`, in committed definitions. Use asset identifiers as
  strings rather than new `Asset` constants in decoders.
- When you need a verified ABI, use Sourcify. For a full match, read `output.abi` from
  `https://repo.sourcify.dev/contracts/full_match/<chainID>/<contract_address>/metadata.json`.
  If adding a claim decoder for an airdrop in the [data repo index](https://github.com/rotki/data/blob/develop/airdrops/index_v2.json),
  update its `has_decoder` flag as needed.
- If an indexer is unavailable, configure a public RPC node in the test via
  `*_manager_connect_at_start` and `WeightedNode(NodeName(...))` and query the tx/receipt/logs there.
  When internal transfers are irrelevant, stub the internal query on the path under test. For a
  single transaction, see `_query_and_save_internal_transactions_for_parent_hash` and its use in
  [`test_morpho_blue.py`](rotkehlchen/tests/unit/decoders/test_morpho_blue.py). Prefer exact hashes
  and deterministic event assertions; keep VCR enabled. Escalate only if RPC data is insufficient.

### User and global DB upgrades

Check the latest upgrade's release docstring against [`docs/changelog.rst`](docs/changelog.rst) or
release tags **before bumping a schema version**. If the upgrade is unreleased, add the step and
assertions to the existing upgrade and test. If already released, add/register the next upgrade,
update the version, and add a test. For a new global DB upgrade, extend the `Literal` in
`rotkehlchen/tests/utils/globaldb.py::patch_for_globaldb_upgrade_to`. Keep the fresh-create schema
in sync either way.

| DB | Version | Upgrade registration | Fresh schema |
| --- | --- | --- | --- |
| User | `ROTKEHLCHEN_DB_VERSION` in `rotkehlchen/db/settings.py` | `rotkehlchen/db/upgrade_manager.py` | `rotkehlchen/db/schema.py` |
| Global | `GLOBAL_DB_VERSION` in `rotkehlchen/globaldb/utils.py` | `rotkehlchen/globaldb/upgrades/manager.py` | `rotkehlchen/globaldb/schema.py` |

The scripts are `upgrades/vN_vN+1.py` under the respective DB package. The packaged
`rotkehlchen/data/global.db` must stay schema-compatible: a version mismatch breaks asset resets
and packaged-DB consistency checks.

**Repackaging after an assets update is not a schema upgrade.** The symptom is
`test_asset_updates_consistency_with_packaged_db` failing as soon as a new assets update lands on
the target branch; repackaging is the fix. Use the target `rotki/assets`
branch's `updates/<N>/updates.sql` (runtime selects the branch via `GITHUB_BASE_REF`, `master` in
production). Set `TARGET_VERSION`, `ASSETS_BRANCH`, and `OUTPUT_DIR`, then run:

```bash
uv run python -m tools.assets_database.main \
  --start-db-path rotkehlchen/data/global.db --target-version "$TARGET_VERSION" \
  --assets-branch "$ASSETS_BRANCH" --update-mode assets --target-directory "$OUTPUT_DIR"
```

Use `assets`, not `remote` or `all`, for an assets-only repackage; those modes can bring in location
mappings from the data repo's `develop` branch. Update the `assets_version` assertion in
`rotkehlchen/tests/unit/globaldb/test_globaldb_consistency.py` and `globaldb_assets_version` in
`rotkehlchen/tests/api/test_database.py`. Diff SQLite `.dump` output before replacing the tracked DB:
only the version and intended asset changes should differ.

### Historical balances

In the context of #12204, “accounting refactor,” “accounting buckets,” and “balance buckets” refer
to the historical-balance engine, not legacy PnL or cost basis. Bucket generation is in
`rotkehlchen/tasks/historical_balances.py`, reads are in `rotkehlchen/balances/historical.py`, and
`event_metrics` lives in `rotkehlchen/db/schema.py`.
Event changes invalidate balances via `rotkehlchen/db/history_events.py`. Start with
`rotkehlchen/tests/unit/test_historical_balances.py` and `rotkehlchen/tests/api/test_historical_balances.py`.

## Code review

- Check unresolved maintainer and reviewer comments first. Read the diff and trace reported issues
  through the actual callers, helpers, runtime validation, and exception paths. Type annotations
  alone are not evidence of runtime validation or immutability.
- Cite exact file/line locations, a concrete triggering condition, and its effect. Verify that
  existing guards don't already handle it. Check error logging, edge cases, hot-path work, and
  tests; use the VCR requirements above for added or changed backend tests.
- Don't claim error handling or validation is missing until you have traced the called function,
  and don't assume it is present because of a type annotation.
- Check dict/list access on external or API data for `KeyError`/`IndexError` and missing or
  malformed fields. Error paths log with context; an empty `except`/`else` says why it is empty.
- Check edge cases: empty inputs, `None`, zero amounts, bounds.
- Look for redundant comparisons, repeated work in loops, and unnecessary queries on hot paths.
- Check spacing and punctuation in user-facing strings and error messages.

## Commits and PRs

- Put related changes in one PR as separate focused commits. Split out only a change that stands
  on its own, such as an independent bug fix.
- Keep commits focused and titles at most 50 characters. For non-trivial bugfixes, features, or
  performance changes, add a body after a blank line describing what changed and why, including the
  root cause for fixes. When closing a known issue, end the body with `Fix #<issue-number>` on its own
  line. Use a multiline message when invoking commit or export helpers.
- When an AI agent creates or amends a commit, append exactly one of each trailer, separated from
  the commit body by a blank line. Use the model selected in the current session and the actual
  harness name/version from runtime metadata. If either cannot be verified, ask before committing;
  don't infer it from a configured default. Keep the issue-closing line above the trailers.

  ```text
  LLM-Model: <provider>/<model-id>
  Harness: <harness-name> <version>
  ```

- Do not add AI `Co-Authored-By` trailers to commits or PRs.

## Memories
- EVM addresses MUST be checksummed:
  ✅ CORRECT: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'
  ❌ WRONG: '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c'
- If you see "Invalid XXX account in DB" it's almost certain the address is not checksummed. Always checksum addresses you use with to_checksum_address
- `string_to_evm_address()` is just a no-op typing function. It will not checksum the literal argument to a checksummed evm address. That means you should make sure to only give checksummed EVM address literals to it
