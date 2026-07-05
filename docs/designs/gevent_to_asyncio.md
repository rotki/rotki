# Removing gevent: asyncio shell, sync core

Design and execution plan for [#10090](https://github.com/rotki/rotki/issues/10090).
This is a living document: status markers are updated by the PRs that do the work, and
direction changes are committed with their reasoning so the document history doubles as
the decision log.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Python bump 3.11 → 3.12/3.13 | not started |
| 1 | Stdlib primitives + spawn seam + gevent import ban | **done** — business logic in phase 1 (~45 files); test files finished in phase 6 |
| 2 | Cooperative cancellation (replaces `greenlet.kill`) | **done** — CancellationToken + checkpoints landed, `greenlet.kill`/`GreenletKilledError` removed, substrate `gevent.Timeout` replaced |
| 3 | DB driver dual-mode (gevent / threading backends) | **done** — gevent-free driver with SchedulingMode, transaction-slot locking replaces poll loops, both-modes tests + stress test, atomicity audit done (crash-class findings fixed) |
| 4 | ASGI server behind a flag (uvicorn + WSGI bridge + native websockets) | **done** — `--api-server-backend asgi` serves REST+`/ws` via uvicorn on one port; gevent stays default; `api-asgi` CI leg |
| 5 | Task orchestration off greenlets (thread-backed Task/TaskSupervisor) | **done** — thread-backed `Task` handles everywhere, `GreenletManager`→`TaskSupervisor`, all `killall` paths now cancel+grace, gevent imports confined to the phase-6 files |
| 6 | The flip: remove monkey patching and gevent | **done** — monkeypatching gone, uvicorn is the only server, THREADING the only DB scheduling default, gevent/geventwebsocket/wsaccel deps deleted, plain pytest |
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
              └── uvicorn (ASGI)
                    ├── WSGI bridge → Flask REST (dispatches to threads)
                    └── native websocket route (/ws, same port)
threads:      ALL business logic, synchronous, unchanged signatures
              ├── main loop thread: 10s Event.wait tick → TaskManager.schedule()
              ├── TaskSupervisor: one daemon thread per background task
              ├── REST async-query tasks: one daemon thread per query
              ├── threading.Semaphore / Lock / Event, time.sleep
              └── DB driver (threading backend, no yield machinery)
```

(As decided in phase 5, orchestration is plain threads rather than tasks on the
asyncio loop: the loop only serves HTTP/websockets. A bounded shared pool was
rejected for now — see the phase 5 notes.)

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

As implemented (the same stdlib-under-monkeypatching trick as phases 1/3, so no
dual mode was needed — a `threading.Thread` runs as a cooperative greenlet today
and as a real thread after the flip; verified experimentally: 5 threads sleeping
0.3s concurrently finish in 0.3s, `threading.Timer` fires cooperatively,
greenlets keep running alongside):

- The seam (`rotkehlchen/concurrency/tasks.py`) got a real `Task` class: a
  handle around one daemon thread that captures result/exception/exc_info,
  runs `run_cancellable` as its top frame when it has a token, exposes
  `dead`/`join()`/`get()`/`add_done_callback()`/`request_cancellation()` and
  keeps the target's `kwargs` (as `greenlet.kwargs` did) so cancellation paths
  can identify what a task works on. Threads do not start on construction:
  orchestrators attach bookkeeping (`task_id`, `api_command`,
  `exception_is_error`) and done-callbacks first, then `start()` — under real
  threads a callback could otherwise observe a half-initialized handle.
  `spawn_later` became a token-aware sleep at the top of the task body.
  `wait()` is deadline-joins. `run_in_native_thread()` was added for the one
  real-OS-thread need (premium sync's CPU-bound DB compress/encrypt), backed
  by gevent's hub threadpool until the flip makes it a direct call.
- **No bounded shared pool, deliberately.** Thread-per-task mirrors the old
  greenlet semantics exactly. A shared bounded pool would deadlock when a
  pooled parent spawn-and-waits on children that queue behind it (the
  aggregator/gate/internal-tx fan-outs run inside API tasks), and background
  tasks are already capacity-gated by `max_tasks_num`, while REST concurrency
  is bounded by the server's request workers. Pool + sizing/queue-latency work
  moves to phase 7 if measurements justify it.
- `GreenletManager` → `TaskSupervisor` (`rotkehlchen/tasks/supervisor.py`;
  `rotkehlchen/greenlets/` is gone, `greenlet_manager` attributes renamed
  `task_supervisor`, `api_task_greenlets` → `api_tasks`, `running_greenlets` →
  `running_tasks`). Same tracking/exception-logging behavior via done-callbacks
  instead of `link_exception`.
- **Every `killall` became cancel + one grace period + abandon** (threads
  cannot be killed): `TaskManager.clear()` only cancels (its tasks are all
  supervisor-tracked; the supervisor's `clear()` right after waits the single
  `DEFAULT_CANCEL_GRACE_SECONDS`), and the REST layer cancels api tasks on
  logout/shutdown the same way. A cancelled task that dies later with an
  arbitrary exception (e.g. on the closed DB of a logged-out user) is logged
  at debug without alerting the user — its token shows the death was asked
  for. `GlobalDBHandler.clear_locks()` still covers locks such tasks held.
  The scheduler main loop stays a 10s `Event.wait` loop, now on a named
  thread — no asyncio needed and identical in both worlds.
- The log adapter tags records with `threading.current_thread().name` (task
  threads carry their task name; raw request greenlets show as Dummy-N) and
  `gevent.getcurrent()`/`get_greenlet_name` are gone. `RestAPI.login_lock`
  became `threading.Lock` for `.locked()`.
- Tests: `gevent.joinall`/`gevent.wait` on task collections became seam
  `wait()`, the two killall-based tests became cancellation-based
  (`test_deadlock_logout` now exercises "cancelled while holding the global DB
  lock"), and the eager thread start exposed a latent mock-signature bug in
  `test_maybe_cancel_running_tx_query_tasks` (its patched query function was
  never actually called under gevent). Raw-greenlet tests (db driver stress,
  websockets regression) are untouched until phase 6.
- The TID251 allowlist now holds only phase-6 entries: `__main__`/wrappers
  (monkeypatch), `server.py` (hub signals), `api/server.py` (gevent WSGI),
  `notifier.py` (geventwebsocket), `concurrency/*` (native-thread helper).

### Phase 6 — The flip

One small PR: remove `monkey.patch_all()` (`__main__.py`, pytest wrapper), asyncio
server becomes the only server, threading DB backend becomes the only backend, delete
gevent/geventwebsocket deps, `pytestgeventwrapper.py` (plain pytest works again) and
the urllib3 hack. Validation: full suite, benchmark comparison against the
mocked-HTTP benchmark infra, manual QA on Linux/macOS/Windows, at least one release
cycle of nightlies before deleting fallback code.

As implemented:

- Entrypoints: `monkey.patch_all()` removed from `__main__.py`,
  `rotkehlchen_mock`, the bench/assets-db tools; `pytestgeventwrapper.py` (and
  its urllib3 LifoQueue hack) deleted — plain `uv run pytest` everywhere
  (Makefile, CI workflows, CLAUDE.md).
- Server: the gevent `WSGIServer`/geventwebsocket path is gone from
  `api/server.py`; the phase-4 uvicorn server is the only one, its loop on a
  dedicated `Task` thread, `--api-server-backend` deleted. `RotkiWSApp` and
  the `WebsocketSubscriber` union are gone: `AsgiWebsocketSubscriber` is the
  only client type and the notifier's per-client locks are `threading.Lock`.
  `server.py` uses stdlib `signal.signal` (main thread waits on a
  `threading.Event`, which stdlib makes signal-interruptible) and the gevent
  hub/DNS-threadpool configuration is gone.
- DB driver: `DEFAULT_SCHEDULING_MODE = THREADING`. The `SchedulingMode` enum
  and the GEVENT branch are dead code for phase 7 to delete; test
  parametrization over GEVENT mode was dropped.
- Seam: `run_in_native_thread()` is a direct call (the caller already runs on
  a real thread); it stays as documentation of offload intent until phase 7.
- Dependencies: gevent, greenlet, gevent-websocket and wsaccel deleted.
  The TID251 gevent import ban stays with an EMPTY allowlist so it cannot
  creep back.
- Tests: all 32 gevent-importing test files converted — `gevent.spawn/joinall`
  → seam `spawn`/`wait`, `gevent.sleep` → `time.sleep` (yield-style `sleep(0)`
  sites became real waits on the actual condition where load-bearing),
  `gevent.Timeout` watchdogs → `time.monotonic()` deadline asserts inside the
  polling loops (threads cannot be interrupted), the websocket test reader
  unblocks its `recv()` by closing the socket, and the notifier-locking
  regression test asserts no task exception instead of the gevent-specific
  `ConcurrentObjectUseError`. The greenlet-switch tracer left the profiling
  tools (`sampler.py` keeps the thread profiler).
- The mid-query DB cancellation test became mode-independent: with preemptive
  threads a canceller thread can fire while a statement runs, so the abort at
  the next progress callback is testable in THREADING mode.
- **Driver fixes the flip exposed** (the dual-mode tests of phase 3 always ran
  under cooperative gevent, so THREADING mode had never been truly preemptive
  until now):
  - A GIL/db-mutex deadlock: pysqlite takes sqlite's connection mutex while
    holding the GIL on several paths (`sqlite3_reset` & co, and
    `set_progress_handler`), while another thread mid-`sqlite3_step` holds
    that mutex with the GIL released and its Python progress callback waits
    for the GIL. Fixed twice over: a per-connection `statement_lock` now
    ensures only one thread is inside sqlite C code per connection at a time
    (sqlite serializes per-step on one connection anyway, so nothing real is
    lost), and `critical_section()` no longer toggles the progress handler in
    THREADING mode (pointless there: the callback already exits early while
    `in_critical_section` is held).
  - `wal_checkpoint()` can hit 'database table is locked' whenever a
    concurrent reader's statement is active between its Python calls --
    a window gevent's cooperative scheduling made unobservable. Checkpoints
    are opportunistic, so it now retries within a 2s deadline and gives up
    with a warning; must-succeed callers (DB upgrades) run without
    concurrency.
- uvicorn runs with `ws_ping_interval/ws_ping_timeout=None`: the `websockets`
  backend otherwise pings clients every 20s and drops them when the pong is
  late (observed flakily in CI-like load: a GIL-starved client answered late,
  got disconnected and its test hung). The old geventwebsocket server never
  pinged; dead clients are already noticed and dropped on failed sends.
- Four latent test races surfaced (all "passed" pre-flip only through
  scheduling accidents): the async-task listing in `test_async` polled right
  after spawning a task and relied on gevent running it to completion within
  the request cycle (same class: `test_query_new_events` asserting DB writes
  right after `assert_ok_async_response`); `test_exchange_events_range_query`
  asserted exactly 3 websocket messages while 6 were in flight -- the old
  reader fixture's 0.2s-per-message throttle hid the other 3; and
  `test_stability_pool` exited its etherscan-mock context before the async
  task that needed the mock ran. All now wait on the actual condition inside
  the right scope. WATCH FOR THIS CLASS in CI: any test that mocks a remote
  and triggers an `async_query` must keep the mock active until the task
  result is fetched, and must not assert side effects before waiting on the
  task.

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
6. **GIL convoy on DB row fetches** (found at the phase-6 flip): each
   `sqlite3_step` releases and reacquires the GIL, so a big fetch running
   next to CPU-bound pure-Python threads waits out the 5ms switch interval
   per step (measured: 20k rows go from 0.02s to 300s+ next to two spin
   loops). gevent had the inverse shape: a CPU-bound greenlet blocked
   everyone entirely. Realistic tasks interleave IO/DB (which release the
   GIL), so the adversarial case should not occur, but phase 7 should
   measure mixed workloads and consider per-read connections and
   `sys.setswitchinterval` tuning.

## Open questions

- uvicorn vs hypercorn (default assumption: uvicorn; no uvloop on Windows).
- 3.12 vs 3.13 for phase 0 (default assumption: 3.12 now, 3.13/3.14 in phase 7).
- Exact worker pool size and whether per-subsystem pools are warranted.
