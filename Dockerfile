# build stage
FROM --platform=$BUILDPLATFORM node:24.18.0-bookworm AS frontend-build-stage

ARG BUILDARCH
ENV CYPRESS_INSTALL_BINARY=0
ENV NODE_OPTIONS="--max-old-space-size=4096"

WORKDIR /app
COPY frontend/ .
# The pnpm store is cached so a rebuild re-resolves rather than re-downloads.
RUN --mount=type=cache,target=/pnpm-store \
    if [ "$BUILDARCH" != "amd64" ]; then \
      apt-get update && \
      apt-get install -y build-essential python3 --no-install-recommends; \
    fi && \
    npm install -g corepack@latest && \
    corepack enable && \
    pnpm config set store-dir /pnpm-store && \
    pnpm install --frozen-lockfile && \
    pnpm run docker:build

FROM rust:1.91-bookworm AS rust-build-stage

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY colibri/ ./colibri
COPY crates/ ./crates
# Build both shipped Rust binaries from their shared workspace. The registry and
# target caches preserve the expensive vendored OpenSSL/SQLCipher build, while
# the single Cargo invocation lets Colibri and Starling reuse common artifacts.
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/tmp/cargo-target \
    CARGO_TARGET_DIR=/tmp/cargo-target \
    cargo build --release --locked -p colibri -p starling && \
    mkdir -p /tmp/dist/colibri/release && \
    mkdir -p /tmp/dist/starling/release && \
    cp /tmp/cargo-target/release/colibri /tmp/dist/colibri/release/colibri && \
    cp /tmp/cargo-target/release/starling /tmp/dist/starling/release/starling

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

# Layout stage: assemble everything the runtime needs, while a shell still
# exists. The final stage is distroless and has none, so nothing can be computed
# there -- the version-stamped core binary has to be resolved here instead.
FROM debian:12-slim AS layout-stage

COPY --from=backend-build-stage /tmp/dist /opt/rotki
COPY --from=rust-build-stage /tmp/dist/colibri/release/colibri /opt/rotki/colibri
COPY --from=rust-build-stage /tmp/dist/starling/release/starling /opt/rotki/starling
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

# Give the core binary a stable name *in place*, rather than symlinking it onto
# /usr/sbin as the nginx-era image did. Two reasons:
#   - `COPY --from` dereferences symlinks, so a symlink would arrive in the final
#     stage as a second full copy of the binary, at a path with no `_internal`
#     directory beside it;
#   - PyInstaller onedir resolves `_internal` relative to the executable it was
#     actually started as, so the binary must stay next to its own bundle.
# Getting this wrong fails at runtime, not build time, with
# "Failed to load Python shared library .../_internal/libpython3.14.so.1.0".
#
# Also clear any setuid/setgid bit on the payload we are about to ship. The
# distroless base has none of its own, so this covers only what we add.
RUN APP=$(find "/opt/rotki" -name "rotki-core-*-linux" | head -n 1) && \
    echo "core binary: ${APP}" && \
    mv "${APP}" /opt/rotki/rotki-core/rotki && \
    find /opt/rotki -perm /6000 -type f -exec chmod a-s {} + || true

# Stage libz into a rootfs tree at its real multiarch path, so the runtime can
# pull it with a single arch-agnostic COPY. Hardcoding /usr/lib/x86_64-linux-gnu
# breaks the arm64 build, where zlib lives under aarch64-linux-gnu; the exact
# patch version in the SONAME symlink target also varies. Resolve the real
# directory here (a shell exists) and copy the SONAME plus its target,
# preserving the symlink with `cp -a`.
RUN set -eux; \
    libz=$(find /usr/lib /lib -name 'libz.so.1' 2>/dev/null | head -n 1); \
    libdir=$(dirname "${libz}"); \
    mkdir -p "/rootfs${libdir}"; \
    cp -a "${libdir}"/libz.so.1* "/rootfs${libdir}/"

# Runtime. nginx is gone, starling is the only externally-bound listener and
# serves the SPA + proxies to the loopback backends. This drops the entire nginx
# userland, python3 (entrypoint.py), and curl (the old healthcheck).
#
# distroless/cc rather than debian:12-slim: it carries glibc plus libgcc_s,
# libm, libdl and libpthread, which is everything the two Rust binaries need,
# along with /tmp and a CA trust store. What it does not carry is a shell, apt,
# dpkg, coreutils, or a single setuid binary -- so the whole escalation class the
# previous base needed stripping simply does not exist here. Nothing in the image
# needs a shell at runtime: CMD and HEALTHCHECK are exec-form, and
# `docker exec <container> /opt/rotki/starling ctl status` execs the binary
# directly. For interactive debugging, use the `:debug` variant, which adds
# busybox.
#
# distroless/base is one rung too far: it omits libgcc_s.so.1, which both colibri
# and starling link, and is only 2.6 MB smaller. Copying libs in to reach it
# would be fragility for nothing.
#
# Two things do have to be brought in:
#   - libz.so.1, which the PyInstaller core bootloader links and distroless does
#     not ship;
#   - the CA trust store. Installing `ca-certificates` with apt would drag
#     openssl (and so libssl3) in as a dependency, and nothing here links the
#     system OpenSSL: colibri and starling use rustls plus a statically vendored
#     OpenSSL in rusqlite, and the core carries its own libssl/libcrypto inside
#     the PyInstaller bundle -- confirmed by reading the running process's memory
#     maps, which resolve to _internal/, never /usr/lib. Copying the bundle keeps
#     TLS working without shipping a CVE-tracked library nothing loads.
FROM gcr.io/distroless/cc-debian12 AS runtime

LABEL maintainer="Rotki Solutions GmbH <info@rotki.com>"

ARG REVISION
ARG ROTKI_VERSION
ENV REVISION=$REVISION
ENV ROTKI_VERSION=$ROTKI_VERSION

COPY --from=layout-stage /rootfs/ /
COPY --from=backend-build-stage /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=layout-stage /opt/rotki /opt/rotki

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
     "--core-binary", "/opt/rotki/rotki-core/rotki", \
     "--colibri-binary", "/opt/rotki/colibri", \
     "--data-dir", "/data", \
     "--logs-dir", "/logs", \
     "--frontend-dir", "/opt/rotki/frontend", \
     "--api-host", "127.0.0.1"]

# Baked-in full-chain probe through starling's own proxy; no curl needed.
# start-period covers core's first-boot global.db init so the container isn't
# flagged unhealthy while it is legitimately still starting.
HEALTHCHECK --start-period=60s --interval=30s --timeout=10s --retries=3 \
    CMD ["/opt/rotki/starling", "healthcheck"]
