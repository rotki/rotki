# build stage
FROM --platform=$BUILDPLATFORM node:20-buster as frontend-build-stage

ARG BUILDARCH
ENV COREPACK_ENABLE_STRICT=0
ENV CYPRESS_INSTALL_BINARY=0
WORKDIR /app
COPY frontend/ .
RUN if [ "$BUILDARCH" != "amd64" ]; then apt-get update && apt-get install -y build-essential python3 --no-install-recommends; fi
RUN npm install -g pnpm@9 && pnpm install --no-optional --frozen-lockfile
RUN pnpm run docker:build

FROM python:3.11-buster as backend-build-stage

ARG TARGETARCH
ARG ROTKI_VERSION
ENV PACKAGE_FALLBACK_VERSION=$ROTKI_VERSION
ARG PYINSTALLER_VERSION=v6.3.0
RUN pip install --upgrade --no-cache-dir uv && uv pip install --system setuptools wheel
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
COPY colibri/ ./colibri
RUN cargo build --target-dir /tmp/dist/colibri --manifest-path ./colibri/Cargo.toml --release

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app
RUN uv pip install --system -r requirements.txt

COPY . /app

RUN if [ "$TARGETARCH" != "amd64" ]; then \
      git clone https://github.com/pyinstaller/pyinstaller.git && \
      cd pyinstaller && git checkout ${PYINSTALLER_VERSION} && \
      cd bootloader && ./waf all && cd .. && \
      uv pip install --system "pyinstaller @ ."; \
    else \
      uv pip install --system pyinstaller==${PYINSTALLER_VERSION}; \
    fi

RUN sed "s/fallback_version.*/fallback_version = \"$PACKAGE_FALLBACK_VERSION\"/" -i pyproject.toml && uv pip install --system "rotkehlchen @ ." && \
    python -c "import sys;from rotkehlchen.db.misc import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    PYTHONOPTIMIZE=2 pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

FROM nginx:1.25 as runtime

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
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

RUN APP=$(find "/opt/rotki" -name "rotki-core-*-linux"  | head -n 1) && \
    echo "${APP}" && \
    ln -s "${APP}" /usr/sbin/rotki && \
    ln -s /opt/rotki/colibri/release/colibri /usr/sbin/colibri

VOLUME ["/data", "/logs", "/config"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/entrypoint.py /opt/rotki
CMD ["/opt/rotki/entrypoint.py"]

HEALTHCHECK CMD curl --fail http://localhost/api/1/ping || exit 1
