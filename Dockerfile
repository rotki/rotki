# build stage
FROM --platform=$BUILDPLATFORM node:24.18.0-bookworm AS frontend-build-stage

ARG BUILDARCH
ENV CYPRESS_INSTALL_BINARY=0
ENV NODE_OPTIONS="--max-old-space-size=4096"

WORKDIR /app
COPY frontend/ .
RUN if [ "$BUILDARCH" != "amd64" ]; then \
      apt-get update && \
      apt-get install -y build-essential python3 --no-install-recommends; \
    fi && \
    npm install -g corepack@latest && \
    corepack enable && \
    pnpm install --frozen-lockfile && \
    pnpm run docker:build

FROM rust:1.91-bookworm AS colibri-build-stage

WORKDIR /app
COPY colibri/ ./colibri
RUN cargo build --target-dir /tmp/dist/colibri --manifest-path ./colibri/Cargo.toml --release

# starling, the PID-1 supervisor that replaces entrypoint.py *and* nginx: it
# spawns core+colibri, serves the SPA and reverse-proxies to them in-process.
FROM rust:1.91-bookworm AS starling-build-stage

WORKDIR /app
COPY crates/ ./crates
RUN cargo build --target-dir /tmp/dist/starling --manifest-path ./crates/Cargo.toml --release -p starling

FROM python:3.14-bookworm AS backend-build-stage

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG TARGETARCH
ARG ROTKI_VERSION
ENV PACKAGE_FALLBACK_VERSION=$ROTKI_VERSION
ARG PYINSTALLER_VERSION=v6.21.0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace

COPY . /app

RUN sed "s/fallback_version.*/fallback_version = \"$PACKAGE_FALLBACK_VERSION\"/" -i pyproject.toml && \
    uv sync --locked --no-dev && \
    if [ "$TARGETARCH" != "amd64" ]; then \
      git clone https://github.com/pyinstaller/pyinstaller.git && \
      cd pyinstaller && git checkout ${PYINSTALLER_VERSION} && \
      cd bootloader && uv run --project /app --no-sync python ./waf all && cd .. && \
      uv pip install "pyinstaller @ ."; \
    else \
      uv pip install pyinstaller==${PYINSTALLER_VERSION}; \
    fi && \
    cd /app && \
    uv run python -c "import sys;from rotkehlchen.db.misc import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    PYTHONOPTIMIZE=2 uv run pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

# Runtime. nginx is gone, starling is the only externally-bound listener and
# serves the SPA + proxies to the loopback backends. This drops the entire nginx
# userland, python3 (entrypoint.py), and curl (the old healthcheck).
#
# Base is debian:12-slim, not distroless: the PyInstaller core bootloader links
# system libz (libz.so.1), which distroless/base does not ship. debian:12-slim
# carries zlib already and keeps a shell for debugging; it is still
# nginx/python-free.
#
# No OpenSSL at all. Nothing here links the system one: colibri and starling use
# rustls plus a statically vendored OpenSSL in rusqlite, and the core carries its
# own libssl/libcrypto inside the PyInstaller bundle -- confirmed by reading the
# running process's memory maps, which resolve to _internal/, never /usr/lib.
#
# What we do need is the CA trust store, and installing `ca-certificates` with
# apt drags openssl (and so libssl3) back in as a dependency. So the bundle is
# copied from a build stage instead, which drops the package entirely rather than
# leaving a CVE-tracked TLS library nothing loads.
FROM debian:12-slim AS runtime

LABEL maintainer="Rotki Solutions GmbH <info@rotki.com>"

ARG REVISION
ARG ROTKI_VERSION
ENV REVISION=$REVISION
ENV ROTKI_VERSION=$ROTKI_VERSION

COPY --from=backend-build-stage /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Strip every setuid/setgid bit. The base ships su, mount, newgrp, passwd and
# friends; none is needed to run rotki, and each is a way for a compromised
# backend to re-enter as root after starling drops to uid 10001. starling also
# sets no_new_privs at startup, which neutralizes these independently, but
# removing them means there is nothing to neutralize.
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + || true

COPY --from=backend-build-stage /tmp/dist /opt/rotki
COPY --from=colibri-build-stage /tmp/dist/colibri/release/colibri /opt/rotki/colibri
COPY --from=starling-build-stage /tmp/dist/starling/release/starling /opt/rotki/starling
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

# Stable launch paths despite the version-stamped core binary name. starling is
# given these via --core-binary/--colibri-binary; the symlinks also keep the
# historical `docker exec` entry points working.
RUN APP=$(find "/opt/rotki" -name "rotki-core-*-linux"  | head -n 1) && \
    echo "core binary: ${APP}" && \
    ln -s "${APP}" /usr/sbin/rotki && \
    ln -s /opt/rotki/colibri /usr/sbin/colibri

VOLUME ["/data", "/logs", "/config"]

EXPOSE 80

# `docker stop` sends SIGTERM → starling's handled shutdown path. Set explicitly
# since the base image's default may differ, and because PID 1 has no default
# signal dispositions: an *unhandled* SIGTERM is ignored, so without starling's
# own handler `docker stop` would hang its full timeout and then SIGKILL.
STOPSIGNAL SIGTERM

# starling as PID 1, with a bare CMD (no shell or tini wrapper) so it really is
# PID 1 and receives the signal directly. Backends bind loopback; only starling's
# proxy is exposed. The port and the core tunables come from ROTKI_HTTP_PORT /
# env / /config/rotki_config.json, never baked in here.
#
# Runs as root (no USER) on purpose: starling binds port 80 and adopts the
# root-owned volumes on upgrade, then drops itself and the backends to uid 10001
# (privilege separation, in-process). `docker run --user <uid>` is honored -
# starling detects it is already non-root and skips the drop.
CMD ["/opt/rotki/starling", "--mode", "docker", \
     "--core-binary", "/usr/sbin/rotki", \
     "--colibri-binary", "/usr/sbin/colibri", \
     "--data-dir", "/data", \
     "--logs-dir", "/logs", \
     "--frontend-dir", "/opt/rotki/frontend", \
     "--api-host", "127.0.0.1"]

# Baked-in full-chain probe through starling's own proxy; no curl needed.
# start-period covers core's first-boot global.db init so the container isn't
# flagged unhealthy while it is legitimately still starting.
HEALTHCHECK --start-period=60s --interval=30s --timeout=10s --retries=3 \
    CMD ["/opt/rotki/starling", "healthcheck"]
