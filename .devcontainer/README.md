# Dev container

A container for working on rotki without installing Python, uv, Node.js, pnpm or
Rust on your machine. It targets `pnpm run dev:web` (backend, colibri and the web
frontend). The Electron app is out of scope.

## Use

You need Docker and an editor that supports dev containers, such as VS Code with
the Dev Containers extension (`ms-vscode-remote.remote-containers`). Open the
repository and run **Dev Containers: Reopen in Container**. The first start runs
`setup.sh` in two stages, `toolchains` and then `deps`, which install the
toolchains and the dependencies. Then:

```sh
cd frontend
pnpm run dev:web
```

The app opens on <http://localhost:8080>. It talks to the API on port 4141, so
both ports have to be free on your machine.

After pulling a change that bumps a toolchain or a lockfile, run
`.devcontainer/setup.sh` again. With no argument it runs both stages and skips
whatever is already current; `setup.sh deps` only reinstalls the dependencies.

### Git worktrees

Only the opened folder is mounted, so in a linked worktree git cannot reach the
main repository's `.git` and fails inside the container. To fix that, enable
`dev.containers.experimentalMountGitWorktreeCommonDir` in your VS Code user
settings. It needs worktrees created with relative paths
(`git worktree add --relative-paths`, or `worktree.useRelativePaths = true`).

### Sharing a checkout with the host

The container leaves the host's own environment in the checkout alone. Its venv
and its `node_modules` folders live in volumes, so you can switch between the
container and the host without reinstalling. Docker creates empty `node_modules`
folders in the checkout to mount those volumes on; on a Linux host they are owned
by root, so remove them before the first `pnpm install` on the host.

## Volumes

| Volume | Holds | Shared |
| --- | --- | --- |
| `rotki-devcontainer-{cargo,rustup,cache,local}` | toolchains and download caches | by every checkout |
| `rotki-devcontainer-<id>-data` | the rotki dev profile: accounts, databases, keys | no, one per checkout |
| `rotki-devcontainer-<id>-venv`, `-nm*` | the Python venv and `node_modules` | no, one per checkout |

Removing the shared volumes only costs a fresh download. Removing a `-data`
volume deletes that checkout's dev profile.

The pnpm store lives in the shared cache volume, on a different filesystem from
each checkout's `node_modules`, so pnpm copies packages instead of hardlinking
them: expect about 800 MB of `node_modules` per checkout.

## Memory

8 GB is enough for `dev:web`. `pnpm run typecheck` (vue-tsc) and the lint run
need several GB more; if they die with "JavaScript heap out of memory", raise
the memory Docker may use.

## Maintenance

There is nothing here to bump. `setup.sh` reads every version from a file the
project already maintains for CI:

| Tool | Source |
| --- | --- |
| Python (free-threaded) | `PYTHON_VERSION` in `.github/.env.ci` |
| Rust | `rust-toolchain.toml` |
| Node.js | `frontend/.nvmrc` |
| pnpm | `packageManager` in `frontend/package.json` |

uv and rustup install their latest release, and the base image tag
(`devcontainers/base:bookworm`) receives Debian security updates on its own.

The one manual step: a new frontend workspace package needs its `node_modules`
added to the mounts in `devcontainer.json`. `setup.sh` stops with a message
naming the folder until it is.

The container is maintained by the contributors who use it. CI does not build
it, so a change elsewhere in the repository never fails because of it.
