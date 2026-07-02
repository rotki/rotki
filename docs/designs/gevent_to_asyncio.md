# Removing gevent: asyncio shell, sync core

Design and execution plan for [#10090](https://github.com/rotki/rotki/issues/10090).
This is a living document: status markers are updated by the PRs that do the work, and
direction changes are committed with their reasoning so the document history doubles as
the decision log.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Python bump 3.11 → 3.12/3.13 | not started |
| 1 | Stdlib primitives + spawn seam + gevent import ban | **in progress** — business logic done (~45 files); test files remain (phases 2-3 exemption) |
| 2 | Cooperative cancellation (replaces `greenlet.kill`) | **done** — CancellationToken + checkpoints landed, `greenlet.kill`/`GreenletKilledError` removed, substrate `gevent.Timeout` replaced |
| 3 | DB driver dual-mode (gevent / threading backends) | **done** — gevent-free driver with SchedulingMode, transaction-slot locking replaces poll loops, both-modes tests + stress test, atomicity audit done (crash-class findings fixed) |
| 4 | ASGI server behind a flag (uvicorn + WSGI bridge + native websockets) | **done** — `--api-server-backend asgi` serves REST+`/ws` via uvicorn on one port; gevent stays default; `api-asgi` CI leg |
| 5 | Task orchestration on the asyncio loop | not started |
| 6 | The flip: remove monkey patching and gevent | not started |
| 7 | Harvest: native-async hot paths, free-threading experiments | not started |

## Why

- gevent requires monkey patching the entire stdlib, which has produced an endless
  stream of edge cases (the sqlite progress-callback machinery, the urllib3 LifoQueue
  workaround in `pytestgeventwrapper.py`, plugin interference in tests).
- gevent and its ecosystem (`gevent-websocket` is unmaintained) are in slow decline.
- gevent is fundamentally incompatible with free-threaded CPython. Removing it is a
  hard prerequisite for real multi-core parallelism once the GIL goes away.
- asyncio is the standard; coroutines at the orchestration layer make the codebase
  approachable to any modern Python developer.

## Decisions (made 2026-06-12)

1. **Hybrid concurrency model.** One asyncio event loop in the main thread owns the
   server, websockets and task scheduling. Business logic stays synchronous and runs
   in a bounded worker-thread pool. Native async conversion of network-heavy layers
   happens later, selectively, where it pays (phase 7). Rationale: avoids the
   function-coloring rewrite of the entire call graph, ships incrementally, and sync
   code in real threads is exactly what benefits from free-threaded Python.
2. **Flask stays.** The REST layer (Flask + webargs + marshmallow) is untouched; it is
   served through a WSGI→ASGI bridge which runs each request in the worker pool. A
   framework migration (e.g. to pydantic-based stacks) is explicitly out of scope.
3. **Incremental on develop.** No long-lived migration branch for the prep work. All
   phases up to 5 land as normal PRs while gevent keeps running; phase 6 is one small
   atomic flip PR. (Initial development happens on the `asyncio-migration` branch,
   merged in reviewable chunks.)
4. **Python bump first.** Phase 0 moves to 3.12/3.13 independently, separating
   interpreter risk from concurrency risk.

## Current gevent footprint (inventory, 2026-06-12)

88 backend files + 32 test files import gevent. Four load-bearing dependencies:

1. **DB driver** (`rotkehlchen/db/drivers/gevent.py`): sqlite progress handler fires
   every 5000 VM instructions and calls `gevent.sleep(0)` to force cooperative yields;
   three semaphores (`in_callback`, `transaction_lock`, `in_critical_section`);
   single-writer enforcement via greenlet id. ~1198 `read_ctx`, ~425 `write_ctx`,
   ~20 `savepoint_ctx` call sites — all isolated behind the context-manager API.
2. **Server** (`rotkehlchen/api/server.py`): one gevent `WSGIServer` serving Flask
   (`^/`) and geventwebsocket (`^/ws`) on the same port. The async-query REST pattern
   spawns a greenlet and lets the client poll `/tasks/<id>`.
3. **GreenletManager + TaskManager**: ~25 periodic background task types from a 10s
   scheduler loop; cancellation via `greenlet.kill(GreenletKilledError)` at arbitrary
   blocking points.
4. **Monkey-patched `requests`**: all network concurrency comes from blocking requests
   calls inside greenlets with patched sockets. There is no native async code and no
   real threading anywhere.

Long tail (mechanical): 31 `gevent.sleep` backoff calls, 6 `spawn`/`joinall` calls at
3 sites (`chain/aggregator.py`, `exchanges/gate.py`, `tasks/internal_tx_conflicts.py`),
~40 semaphores (mostly `@protect_with_lock` in `utils/mixins/lockable.py`), one Event
(`exchanges/exchange.py` session reset), `gevent.Timeout` in
`chain/substrate/manager.py`. No greenlet-local storage.

## Target architecture

```
main thread:  asyncio event loop
              ├── uvicorn (ASGI)
              │     ├── WSGI bridge → Flask REST (runs in worker pool)
              │     └── native websocket route (/ws, same port)
              ├── TaskSupervisor (replaces GreenletManager)
              └── periodic scheduler (replaces TaskManager loop)
worker pool:  bounded ThreadPoolExecutor (~32, IO-bound)
              └── ALL business logic, synchronous, unchanged signatures
                  ├── threading.Semaphore / Lock / Event, time.sleep
                  └── DB driver (threading backend, no yield machinery)
```

- **Cancellation** becomes cooperative: a token checked at defined checkpoints — the
  sqlite progress handler (a truthy return aborts the query natively), retry/backoff
  loops, and pagination boundaries. Kill-anywhere becomes kill-at-checkpoint.
- **Websocket broadcasting**: `RotkiNotifier` keeps per-client asyncio queues; worker
  threads enqueue via `loop.call_soon_threadsafe`.
- The async-query REST contract (task id + polling) is unchanged for the frontend.

## Phases

### Phase 0 — Python bump

3.11 → 3.12/3.13 in an independent PR: sqlcipher3/rotki-sqlite wheel rebuilds,
dependency audit, CI and packaging updates.

### Phase 1 — Stdlib primitives, spawn seam, import ban

Key insight: under `monkey.patch_all()`, stdlib `threading.Semaphore`, `threading.Lock`,
`threading.Event` and `time.sleep` are *already* gevent-cooperative. So the primitive
long tail migrates directly to stdlib — semantically identical today, correct under
real threads after the flip, and nothing to unwind later. Verified: no call site uses
gevent-specific APIs except two `.locked()` checks (those locks become
`threading.Lock`, which has `.locked()`); `.ready()` appears only inside the DB driver.

- `gevent.sleep(x)` → `time.sleep(x)` (including `sleep(0)` yields).
- `gevent.lock.Semaphore` → `threading.Semaphore`; mutex-style ones that need
  `.locked()` → `threading.Lock`. `gevent.lock.RLock` → `threading.RLock`.
- `gevent.event.Event` → `threading.Event`.
- The 3 spawn/joinall fan-out sites move to a minimal seam,
  `rotkehlchen/concurrency/` (`spawn` / `spawn_later` / `joinall`), gevent-backed now,
  thread-pool-backed at the flip. The seam is deliberately tiny: only what has no
  stdlib equivalent.
- ruff `TID251` bans `gevent` / `geventwebsocket` imports everywhere except an
  explicit allowlist (DB driver, greenlets manager, api server/websockets,
  `__main__`, substrate manager, the seam, tests). The allowlist shrinks as phases
  complete; an empty allowlist is the phase-6 precondition.
- `gevent.Timeout` sites in `substrate/manager.py` are NOT seamed — they get bespoke
  redesign in phase 2 (timeouts belong to the underlying IO library, not the
  scheduler).

### Phase 2 — Cooperative cancellation (still on gevent)

Replace `greenlet.kill()` semantics with a cancellation token plumbed through
GreenletManager, TaskManager and the API task-kill path. Checkpoints: DB progress
handler, retry/backoff loops, pagination boundaries. Rewrite the tests that assert
greenlet liveness/death (`tests/api/blockchain/test_evm.py`, `tests/api/test_errors.py`).
Doing this under gevent isolates "did cancellation behavior regress" from "did the
runtime swap break things". Also: redesign the `substrate/manager.py` `gevent.Timeout`
usage onto library-level timeouts.

As implemented:

- `rotkehlchen/concurrency/cancellation.py`: `CancellationToken` (a `threading.Event`,
  gevent-cooperative today, unchanged after the flip), `TaskCancelledError`
  (inherits **BaseException**, like `asyncio.CancelledError`, so broad
  `except Exception` handlers cannot swallow a cancellation), `checkpoint()`,
  `cancellable_sleep()` and `run_cancellable()`. The current task's token lives in a
  `ContextVar`; greenlets do **not** inherit contextvars (verified), so every spawn
  path establishes the token explicitly and the seam's `spawn`/`spawn_later`
  propagate the spawner's token to children — cancelling a task cancels its tree.
- Token holders: `GreenletManager.spawn_and_track` and the REST `_query_async` attach
  a fresh token per task (`greenlet.cancellation_token`);
  `greenlets/utils.py::request_cancellation` is how kill paths request it.
- Kill paths converted: `RestAPI.delete_async_task` and
  `Rotkehlchen.maybe_cancel_running_tx_query_tasks` (ex `maybe_kill_...`). The latter
  cancels matching tasks then waits a short grace (`DEFAULT_CANCEL_GRACE_SECONDS`) so
  account removal does not race their DB writes; a task stuck in a remote query is
  left to die at its next checkpoint. `GreenletKilledError` is gone. Logout/shutdown
  keep `gevent.killall` until phase 5.
- Checkpoints: the DB progress callback returns 1 for a cancelled task, aborting the
  running statement (native sqlite interrupt); the cursor translates the resulting
  `OperationalError('interrupted')` into `TaskCancelledError`. Since `write_ctx` runs
  inside `critical_section` (progress handler disabled), DB aborts hit only reads and
  savepoint bodies; savepoint bookkeeping statements are shielded by holding
  `in_callback`. The driver's transaction/savepoint cleanup now catches
  `BaseException` so cancellation (and `GreenletExit`) rolls back properly, and its
  writer/savepoint wait loops are checkpoints too. All retry/backoff `time.sleep`
  calls became `cancellable_sleep` (~27 files, incl. the token-bucket rate limiter),
  and explicit `checkpoint()` calls sit at the evm tx-query pagination boundaries,
  the decoding loop and the historical-balance processing loop.
- Substrate: `SubstrateInterface` gets `ws_options={'timeout': ...}` for ws(s)
  endpoints and a default-timeout patch on the http transport's requests session;
  `wait_until_a_node_is_available` is a monotonic-deadline loop over
  `cancellable_sleep`. `substrate/manager.py` left the TID251 allowlist.

### Phase 3 — DB driver dual-mode

Make the driver's scheduling/identity mechanism injectable. Threading backend: drop
the yield-every-5000-instructions machinery (threads preempt), keep the progress
handler solely as a cancellation checkpoint, writer identity via
`threading.get_ident()`, semaphores → threading locks. Parametrize the driver tests
(`tests/db/test_savepoints.py`, `tests/db/test_async.py`) over both backends, add a
concurrency stress/soak test. Codebase-wide audit for implicit atomicity assumptions
(code that is race-free only because gevent never switches between non-yielding
statements — e.g. the exchange session-reset machinery).

As implemented:

- The driver has **no gevent import** anymore. Under monkeypatching the stdlib
  primitives it now uses are already gevent-cooperative (`threading.Lock` with
  `.locked()` replacing the semaphores' `.ready()`, `threading.get_ident()` giving a
  distinct ident per greenlet for writer/savepoint identity, `time.sleep`), so
  instead of an injectable backend object the dual mode collapsed to a single
  `SchedulingMode` enum: in GEVENT mode the progress callback yields
  (`time.sleep(0)` → monkeypatched `gevent.sleep(0)`); in THREADING mode it returns
  immediately and remains solely a cancellation checkpoint. The mode comes from the
  `DBConnection(scheduling_mode=...)` param, defaulting to the module's
  `DEFAULT_SCHEDULING_MODE` read at construction time — the phase-6 flip changes
  that one constant.
- **The wait machinery was redesigned, not just translated.** The old poll-a-field
  loops (`while savepoint_greenlet_id is not None: sleep(0.025)`) were check-then-act
  races that only worked because savepoint bookkeeping statements are too small to
  trigger a progress-handler yield — under preemptive threads two tasks could pass
  the check together and interleave SAVEPOINT/BEGIN statements. Now a write
  transaction and the outermost savepoint of a task both claim `transaction_lock`
  ("the transaction slot") via a cancellation-responsive acquire loop
  (`acquire(timeout=0.025)` + `checkpoint()`), and the last savepoint release frees
  it. Nesting within the owning task (write→savepoint, savepoint→write,
  savepoint→savepoint) is detected by ident and takes no lock. Lock order is
  transaction slot BEFORE critical section everywhere (`write_ctx`, `vacuum`,
  `critical_section_and_transaction_lock`) so no deadlock cycle exists, and a waiting
  writer no longer disables the progress handler while it waits.
- Tests: `test_savepoints.py`, `test_async.py` and the cancellation DB tests are
  parametrized over both modes (new `db_scheduling_mode` fixture patches the default
  for `database`-fixture tests), plus a new stress test
  (`tests/db/test_driver_concurrency.py`) mixing writers, rolling-back savepoint
  stacks, savepoint-nested writes and readers on one connection in both modes.

Atomicity audit results (2026-07-02, fixed in phase 3):

- `utils/data_structures.py` LRU caches (`LRUCacheWithRemove`, `DefaultLRUCache`,
  `LRUSetCache`) — every op was a multi-step check-then-act on shared state; these
  back the Inquirer price cache and the AssetResolver caches touched by every task
  (KeyError/corruption class under threads). All operations now hold a per-instance
  lock; `DefaultLRUCache.get` creates defaults atomically; iteration snapshots via
  `snapshot_keys()`.
- `Inquirer.set_oracles_order` appended into live lists that concurrent price
  queries iterate with `zip(strict=True)` (ValueError/wrong-oracle class). Now
  builds locally and rebinds. Same local-build fix in
  `PriceHistorian.set_oracles_order`.

Audit findings accepted/deferred (stale-read severity, revisit before free-threading):

- Exchange auth signing is safe everywhere (all 20 exchanges build per-request
  header dicts; verified). Residual: `edit_exchange_credentials` mutates
  `session.headers` of a session with possibly in-flight requests (user-triggered,
  rare), and the `RecoveringExchangeSession` swap already has its own locking.
- `CachedSettings.get_settings()` returns the live settings object, so a
  multi-field update can be observed partially applied.
- Oracle penalty counters (`utils/mixins/penalizable_oracle.py`) lose increments
  under concurrent failures (penalty just kicks in late).
- Module-level lazy caches (`chain/evm/contracts.py`, `assets/spam_assets.py`,
  `dbhandler._ignored_asset_ids_cache`) can do redundant duplicate work.
- `@cache_response_timewise` is only safe because every use site sits under
  `@protect_with_lock` — do not use it without that.

### Phase 4 — ASGI server behind a flag

uvicorn serving: WSGI bridge (a2wsgi-style) for the unchanged Flask app + a native
websocket route at `/ws` on the same port + `RotkiNotifier` rewrite. Selectable via
CLI flag; gevent server remains the default. CI gets a matrix leg running api and
websocket test groups in the new mode.

As implemented:

- Verified experimentally that uvicorn's asyncio event loop coexists with the still
  active monkeypatching: the loop runs in a dedicated greenlet and its selector is
  gevent's cooperative one, so all other greenlets keep running while it serves;
  a2wsgi's bridge dispatches each request into a "thread" that is a greenlet under
  the patching, so concurrent requests interleave exactly as before (measured: five
  0.5s-sleeping requests complete in ~0.5s through the bridge).
- New `rotkehlchen/api/asgi.py`: `create_asgi_app()` routes `/ws` to a native
  websocket handler and everything else to the Flask app through
  `a2wsgi.WSGIMiddleware`. One port serves both, as with the gevent server.
- `RotkiNotifier` did not need a rewrite after all: `AsgiWebsocketSubscriber`
  duck-types the small surface the notifier uses (`closed` + `send()`). Its `send()`
  enqueues onto a per-client `asyncio.Queue` via `loop.call_soon_threadsafe` and a
  per-connection sender coroutine drains it — the per-client-queue design from the
  plan, hidden behind the existing notifier so both serving modes share one
  implementation. Send failures raise the new `WebsocketSendError`, which the
  notifier handles like `WebSocketError`.
- `APIServer.start(backend=...)` selects the server; `--api-server-backend
  {gevent,asgi}` (default gevent) wires it from the CLI. uvicorn runs with
  `log_config=None` (inherits rotki logging) and `access_log=False` (the Flask
  before/after request hooks already log).
- Tests: `create_api_server` honors `ROTKI_API_SERVER_BACKEND=asgi`, and CI got an
  `api-asgi` matrix leg running the whole api test group (which includes the
  websocket fixture tests) in the new mode.
- Dependencies added: `uvicorn`, `a2wsgi` (and `websockets` promoted from
  transitive to direct as uvicorn's ws protocol backend).

### Phase 5 — Task orchestration on the loop

GreenletManager → TaskSupervisor: background tasks are sync functions dispatched to
the worker pool, tracked by name with the same exception-logging behavior. The
TaskManager 10s scheduler becomes an asyncio periodic task. The async-query REST
pattern keeps its external contract. The seam's `spawn`/`joinall` flips to
thread-pool futures. Worker pool sizing decision (start ~32) + queue-latency logging.

### Phase 6 — The flip

One small PR: remove `monkey.patch_all()` (`__main__.py`, pytest wrapper), asyncio
server becomes the only server, threading DB backend becomes the only backend, delete
gevent/geventwebsocket deps, `pytestgeventwrapper.py` (plain pytest works again) and
the urllib3 hack. Validation: full suite, benchmark comparison against the
mocked-HTTP benchmark infra, manual QA on Linux/macOS/Windows, at least one release
cycle of nightlies before deleting fallback code.

### Phase 7 — Harvest

Convert genuinely hot network layers to native async where measured to pay (first
candidate: EVM multi-node RPC fan-out). Free-threaded CPython (3.13t/3.14)
experiments. Remove transitional dual-mode code.

## Risks

1. **Latent races exposed by preemption.** Cooperative scheduling has silently masked
   unsynchronized shared state for years. The GIL still serializes bytecode after the
   flip, so the immediate risk is moderate — but every such race is a real bug under
   free-threading. Mitigation: phase-3 audit, per-resource locks already in place,
   stress tests.
2. **DB driver invariants** (~1650 call sites depend on them). Mitigation: dual-mode
   parametrized tests + soak before the flip.
3. **Bounded pool vs. cheap greenlets.** Pool sizing and queue latency need
   monitoring so frontend-visible latency does not regress under load.
4. **Checkpoint cancellation** worst case: a stuck HTTP call ignores cancellation
   until its socket timeout. Mitigation: aggressive request timeouts (mostly present).
5. **`requests.Session` mutation under real threads** (exchange session resets).
   urllib3 pools are thread-safe; the session-swap paths get audited in phase 3.

## Open questions

- uvicorn vs hypercorn (default assumption: uvicorn; no uvloop on Windows).
- 3.12 vs 3.13 for phase 0 (default assumption: 3.12 now, 3.13/3.14 in phase 7).
- Exact worker pool size and whether per-subsystem pools are warranted.
