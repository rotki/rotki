# Measurement framework: integration correctness & continuous performance

Status: DRAFT v2 — incorporates first design-review round (2026-06-11)

## 1. Problem

rotki has no per-change ground-truth signal for two things:

1. **Integration correctness.** Backend unit tests are extensive and frontend has
   some unit tests, but nothing verifies that the *assembled app* (backend +
   colibri + frontend) still works and computes correct values after a change —
   especially across the many modes the app supports (modules, settings,
   premium, data shapes) which all depend on user data.
2. **Performance.** Many recent changes are performance-motivated, but there is
   no measurement: no benchmarks (pytest-benchmark, cargo bench, vitest bench
   are all absent), no CI timing tracking beyond `--durations=150`. We cannot
   say whether a change helped, by how much, or whether an unrelated refactor
   regressed a hot path.

Both problems block effective LLM-assisted development: an agent (or a human)
proposing a perf fix has no way to attach a measured number to it, and no way
to prove the app still behaves correctly end-to-end.

## 2. Core insight

Both problems share one missing substrate: **deterministic, realistic user
scenarios that can be booted reproducibly with all external I/O mocked.**

Given "boot the app as *exactly this user*":

- correctness = assertions over the booted app (API contract checks, golden
  values, e2e flows), and
- performance = timings of fixed operations over the same boot, comparable
  across commits.

So the design is one substrate ("golden profiles") with two measurement stacks
on top. It deliberately reuses what already exists:

- e2e infra already boots a **real** backend + colibri + frontend
  (`frontend/app/playwright.config.ts`, `frontend/app/scripts/start-backend.ts`).
- A JSON-RPC record/replay mock server already exists
  (`frontend/app/tests/e2e/rpc-mock/`) with cassette switching.
- A DB seeding bridge already exists (`frontend/app/tests/e2e/scripts/seed-db.py`).
- The frontend already parses every API response through Zod schemas — runtime
  contracts that nobody currently exercises outside the browser.
- Test-data factories exist (`rotkehlchen/tests/utils/factories.py`).
- CI already caches derived data keyed by content hash (`.e2e/data` keyed by
  `global.db` hash) — the same pattern the profile cache will use.

## 3. Layer 0 — Golden user profiles

### 3.1 Profile set

| Name    | Contents                                                                       | Represents / purpose                          |
|---------|--------------------------------------------------------------------------------|-----------------------------------------------|
| `empty` | fresh user, default settings                                                   | boot/login/first-run baseline                 |
| `small` | 4 ETH + 1 BTC accounts, manual balances, a few exchange trades, **~500 history events total**, a few ignored assets | the default-config common user; primary perf gate |
| `defi`  | 5 EVM chains, ~10 accounts, ~5k decoded events incl. swaps/LP/staking, address book, custom assets | decoder/balances/history hot paths            |
| `whale` | **~400k history events, ~25 accounts** across chains + 3 exchanges, years of data, large address book | scaling behavior: pagination, aggregates. Sized to match a known real power user. |

Phase 1 builds `small` and `whale` (the two ends of the spectrum); `empty` is
trivial and added with the bench harness; `defi` follows in a later phase.

### 3.2 Generator design

New package: `tools/scenarios/` (importable as `tools.scenarios`).

```
tools/scenarios/
├── __init__.py
├── __main__.py          # CLI: uv run python -m tools.scenarios build --profile whale --output <dir>
├── base.py              # ProfileBuilder: creates user via DBHandler, then bulk-inserts
├── deterministic.py     # seeded RNG, fixed clock, address/tx-hash/event factories
├── profiles/
│   ├── empty.py
│   ├── small.py
│   ├── defi.py
│   └── whale.py
└── cache.py             # content-addressed local cache (see 3.4)
```

Key decisions:

- **Generated, never committed.** Binary DBs in-repo go stale on every schema
  bump. The generator creates the user DB through `DBHandler` at the *current*
  `ROTKEHLCHEN_DB_VERSION`, so profiles are always schema-correct on any
  branch, including PRs that add migrations.
- **Bulk direct SQL for volume.** User creation, settings, accounts and small
  data go through the normal `DBHandler` APIs (so they stay valid as code
  evolves). The 400k events of `whale` are inserted with batched
  `executemany` directly against the schema — generation must stay in the
  seconds range, not minutes. Event rows are produced by deterministic
  factories layered on `rotkehlchen/tests/utils/factories.py`.
- **`whale` realism: hand-modeled distributions by default.** Synthetic data
  is a valid perf proxy when its *shape* matches reality: query plans and
  timings depend on row counts, value distributions and cardinalities — not on
  whether the data came from real decoders. The default path is therefore a
  set of **explicit, reviewable distribution constants** in the generator
  (events per type/subtype mix, counterparty cardinality and skew,
  events-per-tx-group histogram, distinct-asset skew, notes-length ranges,
  events-per-month timeline), modeled from domain knowledge and tuned so the
  main history queries hit the same indices and orders of magnitude a real
  power-user DB does. These constants live in one file
  (`tools/scenarios/profiles/whale.py`) precisely so they are easy to review
  and adjust when a real-world bug reveals a shape gap.

  *Optional, explicitly not required:* a `tools/scenarios stats` command could
  extract anonymous aggregate statistics from a real DB to calibrate those
  constants. This stays an **opt-in maintainer tool only** — running it
  against a real DB and committing any output demands careful manual review
  of both the script and its output, and the framework must never depend on
  it. Phase 1 ships without it; it gets built only if hand-modeled shapes
  prove insufficient and a maintainer decides the review cost is worth it.
- **Fully deterministic.** One fixed RNG seed per profile; all timestamps are
  fixed constants relative to a frozen "now" (e.g. 2026-01-01), never wall
  clock. Two builds of the same profile at the same schema version are
  byte-stable in content (row data; SQLite page layout may differ, which is
  fine — the cache key is not the file hash).
- **Output layout = a real rotki data dir**: `<output>/users/<profile>/rotkehlchen.db`
  (SQLCipher, fixed password `e2e-password` reusing the e2e convention) plus
  whatever the backend expects next to it. The backend is then booted with
  `--data-dir <output>` unmodified — no special backend mode for data.
- **No network, ever.** Everything inserted is synthetic. Asset identifiers
  used are ones guaranteed in the bundled `global.db` (ETH, BTC, common ERC-20s).

### 3.3 External I/O when the app runs

A booted profile must not reach the internet, both for determinism and CI
hygiene. Crucially, the **task manager stays enabled**: real runs never
disable it, and benchmarks that exclude the background-task machinery would
measure an app that doesn't exist (and leave a known bug-prone subsystem
unmeasured). Consequences:

- Background tasks will fire during measurement, so the external-HTTP mock
  layer is part of the core substrate, not a later add-on:
  - Chain RPC: reuse the existing rpc-mock server + cassettes
    (`frontend/app/tests/e2e/rpc-mock/`).
  - Price oracles / etherscan / other `externalapis`: a small HTTP mock server
    (same record/replay cassette approach, generalized beyond JSON-RPC) that
    the backend is pointed at. Historical prices are additionally seeded into
    `price_history` in the global DB (same mechanism `seed-db.py` uses) so
    most lookups never leave the DB. No backend code is patched; only
    node/oracle/service URLs are configured through existing settings and
    test-environment hooks.
- Background activity is *realistic noise*: it is part of what users
  experience, so it stays in the measurement. The methodology (k samples,
  median, A/B interleaving — §4.2) absorbs it. If phase 2 calibration shows
  task-manager activity makes deltas unstable beyond the acceptance threshold,
  the fallback is a test-env hook that makes the task schedule deterministic
  (fixed order/intervals) rather than disabling it.
- A dedicated `task_manager_cycle` operation (time for one full cycle of due
  background tasks on the `whale` profile) is added to the op registry so the
  scheduler itself has a tracked number.

### 3.4 Caching

Cache key: `profile-{name}-v{ROTKEHLCHEN_DB_VERSION}-{sha256(tools/scenarios/**)[:12]}`.

- **Local**: built profiles stored under `~/.cache/rotki-scenarios/<key>/`;
  `build` is a no-op cache hit unless `--force`.
- **CI**: `actions/cache` with the same key (mirrors the existing `.e2e/data`
  caching). A schema migration or generator change naturally busts the cache.
- `whale` DB size estimate: 150–400 MB — within actions/cache limits; revisit
  with zstd compression if it grows.

## 4. Stack A — Performance

### 4.1 Macro benchmark harness

New package: `tools/bench/`.

```
tools/bench/
├── __main__.py          # CLI: run | compare | report
├── runner.py            # boots backend (subprocess, like start-backend.ts), waits for /api/1/ping
├── operations.py        # registry of measured operations
├── stats.py             # median/min/stddev, A/B significance
└── output.py            # JSON + markdown table emitters
```

**Measured operations v1** (exact endpoint paths confirmed during
implementation; all are async-task endpoints where applicable, timed
end-to-end including task polling at a tight interval):

| id                   | What is timed                                            | Profiles        |
|----------------------|----------------------------------------------------------|-----------------|
| `boot_to_ping`       | backend process start → first successful `/api/1/ping`   | n/a (no user)   |
| `user_unlock`        | login/unlock call → task completion                      | all             |
| `history_events_p1`  | history events query, first page (default sort/filter)   | small, whale    |
| `history_events_deep`| history events query, page at offset ~⅔ of dataset       | whale           |
| `history_events_filtered` | events query with counterparty + asset filter       | whale           |
| `blockchain_balances_cached` | balances endpoint served from DB cache (`ignore_cache=false`) | small, whale |
| `manual_balances`    | manual balances query                                    | small           |
| `netvalue_stats`     | statistics/net value graph data                          | whale           |
| `asset_search`       | levenshtein asset search                                 | any             |
| `task_manager_cycle` | one full cycle of due background tasks (§3.3)            | whale           |

PnL/accounting reports are **deliberately excluded**: the accounting engine is
about to be reworked, so benchmarking the current implementation would create
baselines and golden values that are obsolete on arrival. Accounting
operations join the registry after the rework lands.

The list is a registry, not a closed set — adding an operation is one function
with a decorator. Criteria for inclusion: user-visible, deterministic on a
seeded profile, no network.

**Methodology:**

- Per run: 1 warmup iteration, then k samples (default 5, CLI-overridable).
- Fresh backend process per (profile × repetition-block) so unlock is measured
  cold and caches don't leak across operations that should be cold.
  Within a block, read-only operations may share a process (documented per op).
- Report median, min, max, stddev per op. Median is the headline number
  (robust to scheduler spikes); min is recorded because it approximates the
  noise floor.
- Output: `bench-result.json`:

```json
{
  "meta": {"commit": "...", "branch": "...", "profile": "whale",
            "db_version": 49, "python": "3.11.9", "host": "...", "ts": "..."},
  "results": [
    {"op": "history_events_p1", "samples_ms": [412.1, 398.7, ...],
     "median_ms": 401.3, "min_ms": 396.2, "stddev_ms": 6.1}
  ]
}
```

### 4.2 Comparison — beating runner noise (self-contained, no external services)

GitHub shared runners have ±10–20 % wall-time noise; absolute numbers across
different runs are not comparable. Two mechanisms:

**Per-change: A/B on the same machine.**
`uv run python -m tools.bench compare --base <ref> --profile whale`

1. Creates a git worktree of `<ref>` (merge-base by default) in a temp dir,
   `uv sync`s it (fast, cached).
2. Runs base and head **interleaved** (A B A B …, k blocks each) on the same
   machine, same profile build, back to back. Interleaving neutralizes thermal
   and load drift; same-machine kills cross-runner variance.
3. Emits a delta table (markdown + JSON): per op, base median vs head median,
   delta %, and a significance verdict using a simple
   "delta > 3×pooled stddev" rule — no new dependencies. (With k=5 samples a
   proper Mann-Whitney U has little power anyway; scipy can be added later if
   sample counts are raised.)

This command is the **LLM/dev interface**: the exact same code path runs
locally and in CI, and its output is the measured number every perf PR must
cite.

**Over time: nightly trend.**
Nightly job runs `bench run` on `develop` for `small` + `whale`, appends
results to a **separate repository** (`rotki/benchmark-data`, mirroring the
existing `rotki/test-caching` pattern so perf-bot commits stay out of the main
repo's history) and renders charts/alerts via
`benchmark-action/github-action-benchmark` (supports an external data repo via
a token; no external service). Alert threshold initially 20 % (tuned later),
wired to the existing Discord-notify pattern from `rotki_nightly.yml`.
The trend line catches slow drift that per-PR A/B misses, and gives absolute
history for "did the last month of changes help?".

### 4.3 CI wiring

- Workflow `rotki_benchmarks.yml`:
  - **PR job** (opt-in via the `run-benchmarks` label or a `[bench]` tag in
    the PR title): cached profile build → `bench compare --base origin/$BASE`
    → delta table published to the run's step summary and uploaded as an
    artifact. The job runs unprivileged because fork PRs (rotki's normal
    contribution flow) get a read-only token regardless of declared
    permissions. Concurrency-cancelled on new pushes.
  - **Comment workflow** (`rotki_benchmarks_comment.yml`): triggered by
    `workflow_run` on Benchmarks completion, runs in repo context with
    `pull-requests: write`, downloads the artifact and posts/updates a single
    PR comment (`gh pr comment --edit-last --create-if-none`). Like the
    nightly cron, `workflow_run` only fires once the file reaches the default
    branch; until then the table is visible in the run summary and artifact.
  - **Nightly job**: matrix over the measured rotki branches (`develop`,
    `bugfixes`), each checked out explicitly (the cron only fires from the
    default branch) → `bench run --gha-output` → push datapoint to the
    `rotki/benchmark-data` repo via `github-action-benchmark`
    (customSmallerIsBetter, alert threshold 120 %, fail-on-alert) → Discord
    notification through the existing nightly notifier on failure. The data
    repo keeps a **single `main` branch**: rotki source branches are separated
    as data *series* by directory (`macro/develop`, `macro/bugfixes`) so each
    gets its own trend chart and alert baseline, and GitHub Pages can serve
    all of them. Matrix runs are serialized (both push to the same branch),
    and branches that don't contain the harness yet are skipped gracefully.
- Profile cache: `~/.cache/rotki-scenarios` via `actions/cache`, keyed on
  `tools/scenarios/**`, the packaged global.db and `db/settings.py` (proxy
  for schema-version bumps; over-busting is harmless).
- Runner: `ubuntu-22.04`, same as backend tests. Job budget target: ≤ 15 min
  for PR mode with `small` + `whale` (profile cache hit assumed).
- See §7.1 for the one-time org setup (data repo, token, label).

### 4.4 Micro benchmarks (later phase)

`pytest-benchmark` suite under `rotkehlchen/tests/benchmarks/` for known hot
pure-Python paths (serialization, event aggregation, fval math), run through
`pytestgeventwrapper.py`, excluded from normal test runs (`-m benchmark`).
Initially informational in nightly; per-PR once thresholds are calibrated.
CodSpeed integration was considered and deferred — design keeps the suite
plugin-compatible (`pytest-codspeed` is a drop-in) if we opt in later.

## 5. Stack B — Integration correctness

### 5.1 API contract suite (phase 3 — cheap, high value)

A vitest suite (`frontend/app/tests/contract/`) pointed at a **live backend**
booted on a golden profile — no browser:

- For every API module the frontend uses, perform the real HTTP call and
  validate the response with the *frontend's own Zod schemas* (imported from
  `src/modules/**`). The schemas are the contract; today they are only
  enforced at user runtime.
- Boot/teardown reuses `start-backend.ts` + profile builder; one backend per
  profile, suite runs against `small` first, `whale` for pagination-shaped
  endpoints.
- Runs in regular PR CI (it is seconds-fast after boot) — any backend
  serialization change that would break the frontend fails here, not in a
  user's hands.

### 5.2 Golden-value e2e specs (phase 5)

New Playwright specs that *log into seeded profiles* and assert known values
rather than exercising create-flows:

- dashboard net worth equals the profile's expected total,
- history page shows expected event count / labels / pagination,
- statistics/net-value graph matches expected datapoints.

(Accounting/PnL golden values join after the accounting rework, same reasoning
as §4.1.)

Expected values are emitted by the profile generator itself
(`<output>/users/<profile>/expected.json`) so they cannot drift from the data.
A small mode-matrix (modules on/off, premium on/off) is applied to one profile
only, to keep runtime bounded.

### 5.3 Premium mode

Premium paths (graphs, watchers, higher limits) must be tested and measured —
they are a major mode users run in. **No mock premium server.** A standing
mock server in the public repo would read as a copy-paste recipe for fooling
rotki into premium; instead, the harness applies a *single surgical
monkeypatch at launch*: when the bench/e2e/contract harness boots the backend
in premium mode, it starts it through a thin Python launcher
(`tools/scenarios/launch_backend.py`) that patches the premium object to be
active with very high limits before starting the API server — directly reusing
the existing backend test machinery in `rotkehlchen/tests/utils/premium.py`
(`create_patched_premium`, `VALID_PREMIUM_KEY/SECRET`), which already does
exactly this for backend tests. Nothing new or copyable is published: the
patch lives in the test harness, not in shipped app code, and is no more than
what the open test suite already contains.

This makes "premium user" a profile *mode* (any profile ±premium) rather than
a separate profile, available to the contract suite, golden e2e, and the bench
op registry alike. Known coverage limit: the real premium HTTP client (sync
upload/download against the actual server protocol) is not exercised — the
patch bypasses it by design. That slice stays covered by the existing backend
unit tests around `premium/sync.py`.

### 5.4 API response snapshots (phase 5, optional)

`bench run --snapshot` records canonicalized JSON responses for the contract
endpoints per profile into golden files; CI diffs them. Unintended response
drift becomes a reviewable diff. (Cheap to add once 5.1 exists; explicitly
regenerable via one command.)

## 6. Branch strategy

The framework lands on **`bugfixes`**, not `develop`. Rationale: the majority
of current changes happen on `bugfixes`, and the framework's purpose is that
every change gets a measured number — a develop-only framework is dark exactly
where the work is. This is safe because phases 1–3 are purely additive (new
directories, no production code paths, no new runtime deps), and `bugfixes`
merges up into `develop` regularly so develop inherits it for free.

Constraints this imposes:

- Framework PRs to `bugfixes` must stay strictly additive to production code.
  If a later phase needs a backend hook (e.g. the deterministic task-schedule
  fallback in §3.3), that commit gets individual scrutiny or lands on
  `develop` first.
- The two branches can sit at different DB schema versions. Profiles being
  generated at the current checkout's version (§3.2) handles this; the one
  consequence for `bench compare` is that when base and head differ in schema
  version it must build the profile per side instead of sharing one build.
- CI jobs (phase 4) start non-blocking on `bugfixes`: bench is label-opt-in,
  the contract suite is non-required until proven stable across a release.

## 7. Phasing & acceptance criteria

| Phase | Deliverable | Done when |
|-------|-------------|-----------|
| 1 ✓ | `tools/scenarios` + `small` & `whale` profiles + cache | `uv run python -m tools.scenarios build --profile whale` produces a bootable data dir in ≤ 60 s cold, ≤ 1 s cached; backend boots it (task manager on, no network egress) and unlocks the user; `EXPLAIN QUERY PLAN` of the main history-events queries on the generated DB uses the expected indices |
| 2 ✓ | `tools/bench` run + compare | `bench compare` prints a stable delta table locally; re-running on an unchanged tree shows all ops within noise (no false deltas > threshold) |
| 3 | CI wiring for bench | nightly trend datapoints accumulate in `rotki/benchmark-data`; `run-benchmarks` label produces a PR comment |
| 4 | Micro benchmarks + remaining bench ops (mock layer, `task_manager_cycle`) | nightly informational; calibration doc for thresholds |
| 5 | Contract suite (first frontend-touching phase) | runs locally against a profile-booted backend and in PR CI (non-required); intentionally breaking a serializer field fails it |
| 6 | Golden e2e + premium mode + `defi`/`empty` profiles + snapshots | specs green in e2e CI group; premium mode runs in contract + e2e |

Ordering note: the backend-only stack (profiles → bench → CI → micro) lands
fully before any frontend-touching phase, by maintainer decision — the
framework proves itself in CI on the backend first; the contract suite and
golden e2e follow as the last phases.

### 7.1 One-time setup required by maintainers (phase 3)

The CI wiring needs three things only an org admin can create:

1. **`rotki/benchmark-data` repository** with a `main` branch (can be empty);
   nightly datapoints and trend charts are pushed there by
   `github-action-benchmark` (same external-repo pattern as
   `rotki/test-caching`). `main` stays the only branch — per-rotki-branch
   series live in directories (see §4.3), not branches.
2. **`BENCHMARK_DATA_TOKEN` secret** in the rotki repo: a token with write
   access to `rotki/benchmark-data`.
3. **`run-benchmarks` label** in the rotki repo, which opts a PR into the
   comparison job (alternatively, contributors can put `[bench]` in the PR
   title — no label needed).

## 8. Risks / open questions

- **SQLCipher write throughput** for 400k-row generation — mitigated by
  batched `executemany` inside one transaction; measured in phase 1.
- **Profile realism drift**: synthetic events may miss pathological shapes
  real users have (huge single transactions, weird assets). Mitigation: the
  distribution constants are explicit and reviewable (§3.2), the generator is
  a registry — new shapes get added when a bug shows the gap — and the opt-in
  stats extractor exists as a calibration escape hatch if hand-modeling proves
  insufficient.
- **Task-manager noise**: with the task manager enabled (§3.3), background
  tasks may fire mid-measurement and widen sample variance. Phase 2's
  acceptance criterion (no false deltas on an unchanged tree) is the gate; the
  prepared fallback is a deterministic-schedule test hook, never disabling it.
- **Premium patch coverage gap**: premium mode via monkeypatch (§5.3) never
  talks to the real premium server, so server-protocol drift is invisible to
  this framework. Accepted: that surface is covered by existing backend unit
  tests, and the alternative (a public mock server) was rejected for
  premium-bypass optics.
- **Schema migrations vs direct SQL inserts**: whale's bulk inserts touch raw
  tables, so a migration that changes `history_events` requires updating the
  generator. This is intended (the cache key busts) but adds a maintenance
  touchpoint; kept small by funneling all raw inserts through one module.
- **Frontend perf** is not measured until phase 6 (Playwright traces +
  `performance.mark`). Backend dominates current perf work, so this is
  deliberately last.
- **Colibri**: not benchmarked in v1; `cargo bench`/criterion can join the
  nightly job later using the same profiles.
