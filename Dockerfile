# build stage
FROM node:14-buster as frontend-build-stage

WORKDIR /app
COPY frontend/ .
RUN apt-get update && apt-get install -y build-essential python3
RUN npm install -g npm@7
RUN npm ci
RUN npm run docker:build

FROM python:3.7-buster as backend-build-stage

ARG PYINSTALLER_VERSION=v3.5
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y build-essential zlib1g-dev

RUN git clone https://github.com/sqlcipher/sqlcipher && \
    cd sqlcipher && \
    git checkout v4.4.0 && \
    ./configure \
    --enable-tempstore=yes \
    CFLAGS="-DSQLITE_HAS_CODEC -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS" \
    LDFLAGS="-lcrypto" && \
    make && \
    make install && \
    ldconfig

RUN python3 -m pip install --upgrade pip
COPY ./requirements.txt /app/requirements.txt

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default nightly-2021-03-24 

WORKDIR /app

RUN pip install maturin==0.11.2 py-sr25519-bindings==0.1.2 wheel
RUN pip install -r requirements.txt

COPY . /app

RUN git clone https://github.com/pyinstaller/pyinstaller.git && cd pyinstaller && \
    git checkout ${PYINSTALLER_VERSION} && \
    cd bootloader && \
    ./waf all && \
    cd .. && \
    python setup.py install

RUN pip install -e . && \
    python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

FROM nginx:1.21 as runtime

LABEL maintainer="Rotki Solutions GmbH <info@rotki.com>"

ARG REVISION
ARG ROTKI_VERSION
ENV REVISION=$REVISION
ENV ROTKI_VERSION=$ROTKI_VERSION

RUN apt-get update && \
    apt-get install -y procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=backend-build-stage /tmp/dist /opt/rotki
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

RUN APP=$(find "/opt/rotki" -name "rotkehlchen-*-linux"  | head -n 1) && \
    echo ${APP} && \
    ln -s ${APP} /usr/sbin/rotki

VOLUME ["/data", "/logs"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/docker-entrypoint.sh ./opt/rotki
CMD ["sh", "-c", "exec /opt/rotki/docker-entrypoint.sh"]

HEALTHCHECK CMD curl --fail http://localhost/api/1/ping || exit 1
