# rotki development proxy

The dev-proxy provides two features beyond a plain pass-through to the Python
backend:

1. **Premium components serving** — serves locally-developed premium statistics
   components in place of the production bundle, so you can iterate on them
   without a release.
2. **Async-query mocking** — overrides specific backend responses from a JSON
   file so you can exercise edge cases (slow queries, partial results, errors)
   without changing backend code.

If you need neither, the proxy is just a slow extra hop — the Python backend
already permits CORS from any `http://localhost:*` origin, so the frontend can
talk to it directly.

## Quick start

The proxy is now spawned automatically by `pnpm dev` / `pnpm dev:web` when
either of its features is in use. You usually do **not** need to start it
yourself.

### Premium components

1. Set `PREMIUM_COMPONENT_DIR` in `frontend/app/.env.development.local` (or in
   your shell):

   ```env
   PREMIUM_COMPONENT_DIR=/home/you/development/repos/rotki-premium-statistics
   ```

2. Build the premium bundle inside that directory:

   ```bash
   npm ci
   npm run build
   ```

3. Run `pnpm dev:web` (or `pnpm dev`). You should see `dev-proxy: on (auto)`
   in the startup log — the proxy is now in front of the backend serving your
   local components.

### Async-query mocking

1. Create `frontend/dev-proxy/async-mock.json` (see `async-mock.example.json`
   in this directory for the shape).
2. Run `pnpm dev:web` — the proxy auto-starts because the file exists.

`async-mock.json` is in `frontend/dev-proxy/.gitignore`, so it stays personal.

### Forcing on/off

`pnpm dev:web --proxy` forces the proxy on regardless of auto-detect.
`pnpm dev:web --no-proxy` forces it off — useful for skipping the extra hop
even when you have a premium-components dir set.

## How auto-detection decides

`shouldUseProxy()` in `frontend/scripts/start-dev.ts`:

- `--proxy` / `--no-proxy` flags always win.
- Otherwise, the proxy is **on** if either is true:
  - `PREMIUM_COMPONENT_DIR` is set to a real directory.
  - `frontend/dev-proxy/async-mock.json` exists.
- Otherwise it's **off**.

The detection runs against `process.env` after `frontend/app/.env.development.local`
has been loaded. `frontend/dev-proxy/.env` is **not** consulted by start-dev —
that file is only read by the proxy subprocess itself, so putting
`PREMIUM_COMPONENT_DIR` there alone will not trigger auto-on.

## What the proxy reads

When start-dev spawns the proxy, it overrides the proxy's `PORT` and `BACKEND`
on the spawn env. Anything else (`PREMIUM_COMPONENT_DIR`, etc.) flows through
from the parent `process.env`, then from `frontend/dev-proxy/.env` as a fallback
for keys not already set.

| Variable                  | Source                                                                        | Default                  |
|---------------------------|-------------------------------------------------------------------------------|--------------------------|
| `PORT`                    | start-dev spawn env (slot-aware)                                              | `4243`                   |
| `BACKEND`                 | start-dev spawn env (actual Python REST port)                                 | `http://localhost:4242`  |
| `PREMIUM_COMPONENT_DIR`   | `frontend/app/.env.development.local`, shell env, or `frontend/dev-proxy/.env`| unset                    |

## Running the proxy standalone

Mostly useful if you want the proxy without the rest of the dev stack — for
example, pointing it at an already-running backend in a different terminal.

```bash
pnpm install --frozen-lockfile
pnpm run --filter @rotki/dev-proxy serve
```

In that mode `PORT`, `BACKEND`, and `PREMIUM_COMPONENT_DIR` come from
`frontend/dev-proxy/.env` if it exists, or from the shell. The file is optional:
`PORT` and `BACKEND` have defaults and an unset `PREMIUM_COMPONENT_DIR` just
disables statistics renderer support. Passing them inline works too:

```bash
PREMIUM_COMPONENT_DIR=/path/to/components pnpm run --filter @rotki/dev-proxy serve
```

The frontend then needs `VITE_BACKEND_URL=http://localhost:4243`
(or whatever proxy port you chose) so it routes through the proxy.

> **Heads-up — old workflow:** previous versions of this README documented
> setting `VITE_BACKEND_URL=http://localhost:4243` in
> `frontend/app/.env.development.local` to opt into proxy mode. That trigger has
> been replaced by the auto-detection above; with the new dev:web flow the
> managed env block writes `VITE_BACKEND_URL` for you, pointing at the proxy
> port when on and the backend port when off.

## Async-mock JSON shape

Look into the `async-mock.example.json` file in this directory and copy it to
`async-mock.json`. The structure is:

```json
{
  "/api/1/assets/updates": {
    "GET": [
      {
        "result": { "local_version": 1, "remote_version": 6 },
        "message": ""
      },
      {
        "result": { "local_version": 2, "remote_version": 5 },
        "message": ""
      }
    ]
  }
}
```

You can put the mocked URL on the root of the JSON and under that add the
request verb. The verb's value can either be an object or an array:

A declared mock replaces the response **whatever the backend answered**, including
a rejection: faking a premium endpoint the dev backend answers with 402, or one it
has not implemented, is most of what this is for. The task endpoints are the
exception — they merge into the backend's own answer, so they are left alone
unless it returned a 2xx.

- **Object** — returned every time you query the same endpoint/verb combination.
- **Array** — each request returns the next index. The first request serves
  index `0`, the second serves `1`, etc. When the end is reached the last item
  keeps being returned for any subsequent requests.

## Implementation notes

- The proxy is a plain `node:http` server in front of `httpxy`, the same
  dependency the electron main process uses for its own dev proxy. There is no
  web framework: the routing is one locally-served path plus a catch-all.
- `src/mock-engine.ts` holds all the mocking logic as pure functions over its
  own state, so it is unit-tested directly. `src/index.ts` is only wiring.
- The statistics renderer (`src/mocked-apis/`) is answered locally before
  anything is forwarded, and a preflight for a mocked path is answered from the
  CORS headers alone.
- Responses are proxied with `selfHandleResponse`, and buffered only for the
  requests the engine can rewrite (the task endpoints and mocked paths), so
  everything else still streams straight through. A rewritten body is sent with
  its own `content-length`.
- Request bodies are read up front so the engine can inspect `async_query`,
  then replayed to the backend through httpxy's `buffer` option, so the
  forwarded request stays byte-identical.
- Mock keys are matched exactly: on the full url first, so a key may pin a
  query string, then on the path alone.
- A mocked async query reports as pending for
  `DEFAULT_TASK_COMPLETION_MS` (8s) and completed after that.
- Under `pnpm dev` the proxy is an internal hop **inside** starling
  (`frontend → starling → dev-proxy → core`), so it only ever sees `/api/1/*`.
  `/colibri/*`, `/ws/*` and `/_control` never leave starling. WebSocket
  forwarding (`ws: true`) and the CORS headers therefore matter only when
  something addresses the proxy directly, as in the standalone run below.
- A backend it cannot reach is answered with a 502 rather than left hanging,
  which matters because every `/api/1/*` call now passes through here.

## Tests

```bash
pnpm run test:proxy                              # from frontend/: typecheck + unit tests (what CI runs)
pnpm run --filter @rotki/dev-proxy test:unit     # vitest, the mock engine and helpers
pnpm run --filter @rotki/dev-proxy test:smoke    # the proxy end to end against a stub backend
```

The smoke test starts the real proxy and a stub backend on ports 14998/14999 and
covers what the unit tests cannot reach: pass-through, the locally served
statistics route, CORS, body forwarding, chunked responses and websocket
upgrades. It writes a temporary `async-mock.json` only if you do not have one.
