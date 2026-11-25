#!/usr/bin/env bash
# Installs the rotki toolchain inside the dev container. Safe to re-run: do so
# after pulling a change that bumps a toolchain or a lockfile. README.md lists
# where each version is read from.
set -euo pipefail

cd "$(dirname "$0")/.."
# Also run outside the editor (docker exec), where remoteEnv does not apply.
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"

step() { printf '\n==> %s\n' "$*"; }

# Each workspace package's node_modules must be one of the volumes in
# devcontainer.json. Otherwise pnpm writes the container's install into the
# checkout, replacing the host's own.
shopt -s nullglob
node_modules=(frontend/node_modules)
while read -r pattern; do
  for dir in frontend/$pattern; do
    if [ -f "$dir/package.json" ]; then node_modules+=("$dir/node_modules"); fi
  done
done < <(sed -n "/^packages:/,/^[^ ]/s/^  - ['\"]\{0,1\}\([^'\"]*\).*/\1/p" frontend/pnpm-workspace.yaml)
for dir in "${node_modules[@]}"; do
  if ! mountpoint -q "$dir"; then
    echo "$dir is not a volume. Add it to the mounts in .devcontainer/devcontainer.json." >&2
    exit 1
  fi
done

# The volumes are created root-owned on first use.
sudo chown "$(id -u):$(id -g)" "$HOME/.cargo" "$HOME/.rustup" "$HOME/.cache" "$HOME/.local" \
  "$HOME/.local/share/rotki" "${UV_PROJECT_ENVIRONMENT:?is set in devcontainer.json}" "${node_modules[@]}"

step 'System packages'
# perl and make build the OpenSSL that rusqlite vendors. node-gyp needs a
# python3 on PATH for the Electron rebuild in frontend/app's postinstall; the
# backend uses uv's Python.
packages=(build-essential perl pkg-config python3 xz-utils)
if ! dpkg -s "${packages[@]}" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq --no-install-recommends "${packages[@]}"
fi

step 'Rust'
if ! command -v rustup >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --no-modify-path --profile minimal --default-toolchain none
fi
# With no argument, rustup installs what rust-toolchain.toml names.
rustup toolchain install --no-self-update

step 'Python'
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
fi
# Same flags as the sync dev:web runs on every start, so neither undoes the
# other. --python only picks the free-threaded build CI uses.
python_version=$(sed -n 's/^PYTHON_VERSION=//p' .github/.env.ci | tr -d "\"'[:space:]")
if [ -z "$python_version" ]; then
  echo 'PYTHON_VERSION not found in .github/.env.ci' >&2
  exit 1
fi
uv sync --locked --python "${python_version}t"

step 'Node.js and pnpm'
node_version=$(tr -d 'v[:space:]' < frontend/.nvmrc)
if [ "$(node --version 2>/dev/null)" != "v${node_version}" ]; then
  case "$(uname -m)" in
    x86_64) node_arch=x64 ;;
    aarch64) node_arch=arm64 ;;
    *) echo "unsupported architecture $(uname -m)" >&2; exit 1 ;;
  esac
  rm -rf "$HOME/.local/node"
  mkdir -p "$HOME/.local/node"
  curl -fsSL "https://nodejs.org/dist/v${node_version}/node-v${node_version}-linux-${node_arch}.tar.xz" \
    | tar -xJ --strip-components=1 -C "$HOME/.local/node"
  # Same as the Dockerfile: the bundled corepack can lag behind pnpm's signing keys.
  npm install -g --silent corepack@latest
fi
corepack enable --install-directory "$HOME/.local/bin"
# corepack reads packageManager from the current directory, so --dir is not enough.
cd frontend
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 pnpm install --frozen-lockfile

step 'Ready: cd frontend && pnpm run dev:web'
