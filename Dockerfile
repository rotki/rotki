# build stage
FROM --platform=$BUILDPLATFORM node:16-buster as frontend-build-stage

ARG BUILDARCH
WORKDIR /app
COPY frontend/ .
RUN if [ "$BUILDARCH" != "amd64" ]; then apt-get update && apt-get install -y build-essential python3 --no-install-recommends; fi
RUN npm install -g npm@8 && npm ci
RUN npm run docker:build

FROM python:3.9-buster as backend-build-stage

ARG TARGETARCH
ARG ROTKI_VERSION
ENV PACKAGE_FALLBACK_VERSION=$ROTKI_VERSION
ARG PYINSTALLER_VERSION=v5.2
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN if [ "$TARGETARCH" != "amd64" ]; then curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y; fi
ENV PATH="/root/.cargo/bin:${PATH}"
RUN if [ "$TARGETARCH" != "amd64" ]; then rustup default nightly-2021-03-24; fi

RUN python3 -m pip install --upgrade pip setuptools wheel
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app

RUN if [ "$TARGETARCH" != "amd64" ]; then \
      git clone https://github.com/pyinstaller/pyinstaller.git && \
      cd pyinstaller && git checkout ${PYINSTALLER_VERSION} && \
      cd bootloader && ./waf all && cd .. && \
      python setup.py install; \
    else \
      pip install pyinstaller==${PYINSTALLER_VERSION}; \
    fi

RUN pip install --no-use-pep517 -e . && \
    python -c "import sys;from rotkehlchen.db.misc import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    PYTHONOPTIMIZE=2 pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

FROM nginx:1.21 as runtime

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
    ln -s "${APP}" /usr/sbin/rotki

VOLUME ["/data", "/logs", "/config"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/entrypoint.py /opt/rotki
CMD ["sh", "-c", "/opt/rotki/entrypoint.py"]

HEALTHCHECK CMD curl --fail http://localhost/api/1/ping || exit 1
