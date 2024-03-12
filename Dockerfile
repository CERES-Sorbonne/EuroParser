FROM python:3.11-bullseye
LABEL authors="Marceau-h"

ENV EUROPARSER_OUTPUT=/output
EXPOSE 8000

RUN mkdir -p /output
RUN mkdir -p /logs

COPY . /app

WORKDIR /app

RUN pip install -U pip

RUN pip install .

ENTRYPOINT ["python", "-m", "uvicorn", "src.europarser.api.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8", "--timeout-keep-alive", "1000", "--log-config", "docker_log.conf"]
