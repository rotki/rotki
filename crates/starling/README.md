# starling

The rotki backend supervisor: one process that owns the lifecycle of `rotki-core`
(the python API) and `colibri` (the rust service), and exposes control over a
private RPC channel.

The Electron app spawns a single `starling` child instead of managing the two
backends itself.

## Why it exists

The startup contract - *spawn in dependency order → gate on readiness →
supervise → shut down in reverse order* - used to be implemented three times over
(`entrypoint.py`, `process-manager.ts`, `subprocess-handler.ts`), each with its
own bugs and none of them sharing a definition of "ready". starling expresses it
once, over a declarative service graph, and makes the process tree genuinely
owned rather than merely spawned.

## Layout

| Crate           | Role                                                                                                                                                                           |
|-----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `starling-core` | The lifecycle engine: service graph, readiness gating, process-tree termination, control vocabulary. Platform code sits behind traits so the engine is unit-testable headless. |
| `starling`      | The supervisor binary: builds the `[core, colibri]` graph from CLI args and drives it over an NDJSON stdio control channel.                                                    |

## Architecture

```
electron main
   │  spawn + stdio pipes
   ▼
starling ──────────────── control channel (NDJSON on stdin/stdout)
   │
   ├── rotki-core   (readiness-gated on /api/1/ping)
   └── colibri      (readiness-gated on its port)
```

**Boots idle.** starling does not auto-start the tree. It comes up, serves the
control channel immediately, and waits for the renderer's first `start` request
(which carries the backend options the CLI deliberately does not take). A
transport that subscribed before `start` is therefore guaranteed to observe the
`ready` event - there is no startup race.

**Reads and mutations take different paths.** Mutations (`start`/`restart`/`stop`)
are queued to the single run loop and serialized. Reads (`status`/`health`) are
served from a `watch` snapshot and never enter that queue, so a read stays
responsive during a multi-second restart (reporting not-ready, which is correct).

**Shares Electron's lifecycle.** stdin EOF means the parent is gone, and triggers
the same ordered shutdown a signal does. starling cannot orphan a backend by
outliving its parent.

**Holds a data-directory lock**, so a second instance cannot attach to a directory
already in use (exit code `3`, which Electron maps to a user-facing "already
running" error rather than a crash).

### Process ownership

The part that is easy to get wrong, so stated explicitly:

- Each service is spawned into **its own process group** (unix) / a **Job Object**
  plus `CREATE_NEW_PROCESS_GROUP` (windows).
- `terminate()` is graceful and **tree-wide**: `SIGTERM` to the group, or
  `CTRL_BREAK` to the group on windows.
- `kill()` is forceful and tree-wide: `SIGKILL`, or `TerminateJobObject`.
- `wait()` covers only the **direct child**; `tree_alive()` covers the rest.
  Shutdown waits for both - a service is not "stopped" until its tree is empty.
  Otherwise a service whose real work happens in a descendant is reported stopped
  early and then reaped mid-shutdown (how a backend loses its database close).
- Job Objects carry `KILL_ON_JOB_CLOSE`, so if starling itself dies the tree is
  reaped rather than orphaned.

Shutdown is graceful-then-forceful, in reverse dependency order, bounded by
`--shutdown-grace-secs` per service. Bring-up races the shutdown signal, so a quit
arriving mid-startup is honored immediately instead of waiting out the readiness
budget (~5 min worst case for core's ping gate).

**Dev launches the same shape as packaged**: services are spawned directly, never
through a launcher wrapper (`uv run`, `cargo run`). A wrapper reintroduces the
`wait()`-vs-tree gap above - it can die faster than the service it launched and
report a false "stopped". The dev launcher resolves the interpreter and uses the
prebuilt binaries instead.

## Control RPC

JSON-RPC 2.0, newline-delimited, over stdin/stdout. stdout is a **private control
channel**: logs go to stderr, and children are spawned with stdin/stdout detached
so they can neither read requests nor corrupt the response stream.

Stdio is the only transport. It is trusted by construction - no other process can
address a private parent↔child pipe - so the whole surface is available on it.
(`protocol::is_authorized` is written as a transport × method matrix because the
vocabulary is shared with `starling-core`, but this binary only ever serves
`Transport::Stdio`.)

### Methods

| Method    | Kind     | Meaning                                                                   |
|-----------|----------|---------------------------------------------------------------------------|
| `health`  | read     | Minimal boolean liveness (`ok`, `degraded`).                              |
| `status`  | read     | Detailed snapshot: per-service state, pids, restarts, `started_at`.       |
| `start`   | mutating | Bring the tree up from idle with the initial options. Replies once ready. |
| `restart` | mutating | Reconfigure and restart in place (may switch data directory).             |
| `stop`    | mutating | Ordered teardown, then supervisor exit.                                   |

Mutations are rate-limited (2s minimum spacing) and audit-logged. `loglevel` is
validated; `data_directory`/`log_directory` are accepted here because stdio is the
desktop, where the user genuinely chooses a folder.

### Events (notifications, server → client)

| Event        | Payload                         |
|--------------|---------------------------------|
| `ready`      | `services`                      |
| `crashed`    | `service`, `code`, `last_error` |
| `restarting` | `reason`                        |
| `stopped`    | -                               |

Crashes are **surfaced, not auto-restarted**: a service exiting unexpectedly emits
`crashed` and ends the supervise loop.

## CLI

Launchers are passed in rather than discovered, so the same binary serves dev
(resolved interpreter + built binaries) and packaged (bundled executables).

```
--core-binary <path>        --colibri-binary <path>
--core-prefix <arg>...      --colibri-prefix <arg>...   (repeatable)
--core-cwd <dir>            --colibri-cwd <dir>
--core-port <port>          --colibri-port <port>
--data-dir <dir>            --logs-dir <dir>
--api-host <host>           --api-cors <patterns>
--shutdown-grace-secs <n>   (default 10, per service)
```

The mutable backend tunables (log level, logfile counts, sqlite instructions, …)
are deliberately **not** CLI args - the renderer sends them in `start`/`restart`,
so they live in one place instead of being mirrored on both the CLI and the RPC.

Exit codes: `0` clean, `1` a service crashed, `3` data directory already in use.

## Tests

```bash
cargo test --locked                            # engine + cross-platform
cargo test --locked --test windows_lifecycle   # windows-only (own CI runner)
cargo test --locked --test posix_lifecycle     # posix-only
```

The engine is tested headless with a fake spawner. Platform process-tree behavior
needs real processes, so it lives in integration tests driven by the
`fake_bootloader` fixture. One test is `#[ignore]`d because it needs a pyinstaller
bundle built first - see the header of `tests/process_tree_python_bundle.rs`.
