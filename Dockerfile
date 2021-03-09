# build stage
FROM node:lts-alpine as frontend-build-stage

WORKDIR /app
COPY frontend/app/package*.json ./
RUN if ! npm ci --exit-code; then npm ci; fi
COPY frontend/app/ .
RUN npm run build -- --mode docker

FROM python:3.7 as backend-build-stage

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app

RUN pip install -e . && \
    pip install pyinstaller==3.5 && \
    python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)" && \
    pyinstaller --noconfirm --clean --distpath /tmp/dist rotkehlchen.spec

FROM nginx:stable as runtime

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
COPY --from=frontend-build-stage /app/dist /opt/rotki/frontend

RUN APP=$(find "/opt/rotki" -name "rotkehlchen-*-linux"  | head -n 1) && \
    echo ${APP} && \
    ln -s ${APP} /usr/sbin/rotki

VOLUME ["/data", "/logs"]

EXPOSE 80

COPY ./packaging/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./packaging/docker/docker-entrypoint.sh ./opt/rotki
CMD ["sh", "-c", "exec /opt/rotki/docker-entrypoint.sh"]

HEALTHCHECK CMD curl --fail http://localhost/api/1/users || exit 1
