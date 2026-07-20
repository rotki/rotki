# rotki Docker image

The image runs three processes: **starling**, a supervisor that is PID 1, plus
the two backends it owns, **rotki-core** (the Python API) and **colibri**.

starling replaces what used to be two separate pieces:

- the old `entrypoint.py`, which spawned the backends; and
- the bundled **nginx**, which served the frontend bundle and reverse-proxied to
  the backends. starling now does this in-process.

Only starling binds an external port. The backends listen on loopback inside the
container and are not reachable from outside it.

## Running

```bash
docker run -p 8080:80 \
  -v ~/.rotki/data:/data \
  -v ~/.rotki/logs:/logs \
  rotki/rotki
```

The web UI is then on <http://localhost:8080>.

### Hardened run

None of these can be baked into the image, they are runtime flags:

```bash
docker run -p 8080:80 \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --read-only --tmpfs /tmp --tmpfs /run \
  -v ~/.rotki/data:/data \
  -v ~/.rotki/logs:/logs \
  rotki/rotki
```

`--read-only` is possible because there is no nginx cache or run directory left.
Two writable mounts are still required: `/tmp` for the startup temp sweep and the
backends' scratch files, and `/run` for starling's control socket.

### Users and permissions

The container starts as **root on purpose**: starling needs it to bind port 80
and to adopt ownership of volumes created by an older release. It then drops
itself *and* both backends to uid/gid `10001` and never regains privilege.

`docker run --user <uid>` is honored. starling detects that it is already
non-root, skips the drop, and the backends inherit those credentials. The volumes
must then already be writable by that uid.

**Your mounted `/data` and `/logs` become owned by uid 10001.** That is what lets
the unprivileged backends write to them, and it happens on first start. On the
host those files will no longer be owned by your own user, so removing or editing
them directly needs `sudo`, or a throwaway container:

```bash
docker run --rm -v ~/.rotki/data:/data debian:12-slim rm -rf /data/some-file
```

Two things make that drop stick, neither of which depends on you passing a flag:

- starling sets `no_new_privs` before starting anything, so no process in the
  tree can regain privilege through a setuid binary. This is the same protection
  as `--security-opt=no-new-privileges`, applied whether or not you pass it.
- the image has no setuid or setgid binaries at all; the ones the base image
  ships (`su`, `mount`, `passwd` and friends) have their bits stripped at build
  time, since rotki needs none of them.

## Configuration

Precedence is **`/config/rotki_config.json` > environment > built-in default**.
Every resolved value is logged at startup with the layer it came from, so
`docker logs` shows exactly what took effect.

| Variable | Default | Meaning |
|---|---|---|
| `ROTKI_HTTP_PORT` | `80` | Port starling serves on *inside* the container |
| `LOGLEVEL` | `critical` | Backend log level |
| `LOGFROMOTHERMODULES` | `false` | Include third-party library logs |
| `MAX_LOGFILES_NUM` | backend default | Rotated log files to keep |
| `MAX_SIZE_IN_MB_ALL_LOGS` | backend default | Total log size budget |
| `SQLITE_INSTRUCTIONS` | backend default | SQLite instructions-per-context |
| `ROTKI_SESSION_KEY` | unset | Enables session-cookie auth (see below) |

To mount a config file:

```bash
docker run -v ~/.rotki/config:/config ... rotki/rotki
```

```json
{ "loglevel": "debug", "max_logfiles_num": 5 }
```

> **A malformed `/config/rotki_config.json` now refuses to boot the container.**
> The previous entrypoint logged the error and continued with defaults. Since the
> file is a top-priority admin override, continuing would run a configuration the
> admin believes is not in effect, so it is a hard error instead.

Configuration is read **once at boot**. It is deliberately not settable at
runtime: under `--read-only` a change could not persist, so it would silently
revert on the next restart. To change configuration, recreate the container.

## Health

```
HEALTHCHECK CMD ["/opt/rotki/starling", "healthcheck"]
```

The probe goes through starling's own proxy to `/api/1/ping`, so a pass means the
external listener is up *and* successfully reaching core. It needs no `curl`, and
resolves `ROTKI_HTTP_PORT` the same way the server does, so a custom port keeps
the two in agreement automatically.

## Logs

Access logs are written to stdout in the standard **NCSA combined** format, the
same format the bundled nginx produced, so goaccess, awstats and similar tools
parse them without configuration:

```
203.0.113.9 - - [20/Jul/2026:12:36:56 +0000] "GET /api/1/ping HTTP/1.1" 200 54 "-" "Mozilla/5.0"
```

Note that the backends write their own output to the same stream, so `docker
logs` is a mix of access lines and backend logs. Analyzers skip lines they cannot
parse, so feeding them the whole stream works, but filter it first if you want a
clean access log.

The container's own periodic health probe is excluded, so it does not bury real
traffic. The byte count is the number of bytes actually sent, so it stays correct
for compressed responses.

### Client IPs behind a reverse proxy

If you run rotki behind another reverse proxy, which is how an authenticating
front end is normally added, starling logs the **real client IP** from
`X-Forwarded-For` rather than your proxy's address.

That header is only believed when the connecting peer is trusted, since anything
else would let a client forge log entries. Trusted by default: private (RFC1918),
unique-local, link-local and loopback addresses, which covers a proxy on a Docker
or Compose network. The chain is walked from the right, so a forged entry
prepended by the client cannot displace the address your proxy actually recorded.

If your proxy reaches rotki from a **public** address, declare it:

```
--trusted-proxy 198.51.100.0/24
```

Repeatable, and accepts a bare address for a single host. Without it that
proxy's own address is logged, never the header it sends.

## Administration

A control socket is available at `/run/starling/ctl.sock`, restricted to uid 0:

```bash
docker exec <container> /opt/rotki/starling ctl status
docker exec <container> /opt/rotki/starling ctl health
docker exec <container> /opt/rotki/starling ctl restart
```

`restart` bounces the backends with the configuration starling booted with; it is
for un-wedging, not for reconfiguration, and accepts no options. There is
deliberately no remote `stop`: starling is PID 1, so stopping it stops the
container, and with a `no` or `on-failure` restart policy the container would
then stay down. Use `docker stop`.

## Session-cookie authentication

Setting a stable `ROTKI_SESSION_KEY` enables cookie-based auth:

```bash
docker run -e ROTKI_SESSION_KEY="$(openssl rand -hex 32)" ... rotki/rotki
```

The value is inherited by both backends, which sign and validate the cookie with
it. Keep it stable across restarts or existing sessions are invalidated. Note it
is visible in `/proc/<pid>/environ` to the owning uid, the same exposure the
previous entrypoint had.

## Shutdown

`docker stop` sends `SIGTERM`, which starling handles: it stops the backends in
reverse dependency order, giving core time to close its database, then exits. The
image sets `STOPSIGNAL SIGTERM` and uses a bare `CMD` with no shell wrapper so
starling is genuinely PID 1 and receives the signal directly.
