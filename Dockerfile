# syntax = docker/dockerfile:experimental

FROM python:3.12-slim-bullseye
LABEL authors="Marceau-h"

## MODIFIABLE VARIABLES
ENV EUROPARSER_HOST="0.0.0.0"
ENV EUROPARSER_PORT="8000"
ENV EUROPARSER_WORKERS="8"
ENV EUROPARSER_TIMEOUT_KEEP_ALIVE="1000"

RUN mkdir -p /output /logs

COPY . /app
WORKDIR /app

ENV BUILD_DEPS="build-essential libssl-dev libffi-dev libcurl4-openssl-dev libxml2-dev libxslt-dev \
libjpeg-dev zlib1g-dev python3-dev"

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS

RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip \
    && pip install .

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    apt-get purge -y --auto-remove $BUILD_DEPS \
    && apt-get install -y --no-install-recommends python3 \
    && apt-get autoremove -y

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache /var/cache

## DO NOT MODIFY
ENV EUROPARSER_OUTPUT=/output
EXPOSE 8000

ENTRYPOINT python -m uvicorn src.europarser.api.api:app --host $EUROPARSER_HOST --port $EUROPARSER_PORT --workers $EUROPARSER_WORKERS --timeout-keep-alive $EUROPARSER_TIMEOUT_KEEP_ALIVE --log-config docker_log.conf
