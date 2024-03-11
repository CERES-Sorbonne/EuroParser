FROM python:3.11-bullseye
LABEL authors="Marceau-h"

ENV EUROPARSER_OUTPUT=/output
EXPOSE 8000

RUN mkdir -p /output
RUN mkdir -p /logs

COPY . /app

WORKDIR /app

RUN pip install -U pip

RUN pip install -r requirements.txt
RUN pip install -r requirements-api.txt

ENTRYPOINT ["python", "-m", "uvicorn", "europarser_api.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8", "--timeout-keep-alive", "1000", "--log-config", "docker_log.conf"]
