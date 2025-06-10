# build stage
FROM --platform=$BUILDPLATFORM node:22-bookworm AS frontend-build-stage

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

FROM rust:1-bookworm AS colibri-build-stage

WORKDIR /app
COPY colibri/ ./colibri
RUN cargo build --target-dir /tmp/dist/colibri --manifest-path ./colibri/Cargo.toml --release

FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS backend-build-stage

ARG TARGETARCH
ARG ROTKI_VERSION
ENV PACKAGE_FALLBACK_VERSION=$ROTKI_VERSION
ARG PYINSTALLER_VERSION=v6.7.0

WORKDIR /app
COPY pyproject.toml uv.lock* ./

RUN uv sync --locked --no-dev --no-install-project

COPY . /app

RUN if [ "$TARGETARCH" != "amd64" ]; then \
      git clone https://github.com/pyinstaller/pyinstaller.git && \
      cd pyinstaller && git checkout ${PYINSTALLER_VERSION} && \
      cd bootloader && ./waf all && cd .. && \
      uv pip install "pyinstaller @ ."; \
    else \
      uv pip install pyinstaller==${PYINSTALLER_VERSION}; \
    fi && \
    cd /app && \
    sed "s/fallback_version.*/fallback_version = \"$PACKAGE_FALLBACK_VERSION\"/" -i pyproject.toml && \
    uv pip install -e . && \
    uv run python -c "import sys;from rotkehlchen.db.misc import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    PYTHONOPTIMIZE=2 uv run pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

FROM nginx:1.26 AS runtime

LABEL maintainer="Rotki Solutions GmbH <info@rotki.com>"

ARG REVISION
ARG ROTKI_VERSION
ENV REVISION=$REVISION
ENV ROTKI_VERSION=$ROTKI_VERSION

RUN apt-get update && \
    apt-get install -y procps python3 --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=backend-build-stage /tmp/dist /opt/rotki
COPY --from=colibri-build-stage /tmp/dist/colibri/release/colibri /opt/rotki
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

RUN APP=$(find "/opt/rotki" -name "rotki-core-*-linux"  | head -n 1) && \
    echo "${APP}" && \
    ln -s "${APP}" /usr/sbin/rotki && \
    ln -s /opt/rotki/colibri /usr/sbin/colibri

VOLUME ["/data", "/logs", "/config"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/entrypoint.py /opt/rotki
CMD ["/opt/rotki/entrypoint.py"]

HEALTHCHECK CMD ["curl", "--fail", "http://localhost/api/1/ping"]
