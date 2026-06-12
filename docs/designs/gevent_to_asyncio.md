# Removing gevent: asyncio shell, sync core

Design and execution plan for [#10090](https://github.com/rotki/rotki/issues/10090).
This is a living document: status markers are updated by the PRs that do the work, and
direction changes are committed with their reasoning so the document history doubles as
the decision log.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Python bump 3.11 → 3.12/3.13 | not started |
| 1 | Stdlib primitives + spawn seam + gevent import ban | **in progress** |
| 2 | Cooperative cancellation (replaces `greenlet.kill`) | not started |
| 3 | DB driver dual-mode (gevent / threading backends) | not started |
| 4 | ASGI server behind a flag (uvicorn + WSGI bridge + native websockets) | not started |
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

### Phase 3 — DB driver dual-mode

Make the driver's scheduling/identity mechanism injectable. Threading backend: drop
the yield-every-5000-instructions machinery (threads preempt), keep the progress
handler solely as a cancellation checkpoint, writer identity via
`threading.get_ident()`, semaphores → threading locks. Parametrize the driver tests
(`tests/db/test_savepoints.py`, `tests/db/test_async.py`) over both backends, add a
concurrency stress/soak test. Codebase-wide audit for implicit atomicity assumptions
(code that is race-free only because gevent never switches between non-yielding
statements — e.g. the exchange session-reset machinery).

### Phase 4 — ASGI server behind a flag

uvicorn serving: WSGI bridge (a2wsgi-style) for the unchanged Flask app + a native
websocket route at `/ws` on the same port + `RotkiNotifier` rewrite. Selectable via
CLI flag; gevent server remains the default. CI gets a matrix leg running api and
websocket test groups in the new mode.

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
