# build stage
FROM node:16-buster as frontend-build-stage

WORKDIR /app
COPY frontend/ .
RUN apt-get update && apt-get install -y build-essential python3
RUN npm install -g npm@8
RUN npm ci
RUN npm run docker:build

FROM python:3.9-buster as backend-build-stage

ARG PYINSTALLER_VERSION=v4.8
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

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default nightly-2021-03-24

RUN python3 -m pip install --upgrade pip setuptools wheel
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app
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
    apt-get install -y procps python3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=backend-build-stage /tmp/dist /opt/rotki
COPY --from=frontend-build-stage /app/app/dist /opt/rotki/frontend

RUN APP=$(find "/opt/rotki" -name "rotkehlchen-*-linux"  | head -n 1) && \
    echo ${APP} && \
    ln -s ${APP} /usr/sbin/rotki

VOLUME ["/data", "/logs", "/config"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/entrypoint.py ./opt/rotki
CMD ["sh", "-c", "/opt/rotki/entrypoint.py"]

HEALTHCHECK CMD curl --fail http://localhost/api/1/ping || exit 1
