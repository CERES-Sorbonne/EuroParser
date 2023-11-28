#!/bin/bash

export EUROPARSER_SERVER=https://ceres.huma-num.fr/europarser
export EUROPARSER_PORT=8001

git pull origin master

source venv/bin/activate
pip3 install -U pip
pip3 install -r requirements.txt --quiet
pip3 install -r requirements-api.txt --quiet

IS_RUNNING=$(ps -aux | grep gunicorn | grep europarser_api)
if [ -z "$IS_RUNNING" ]
then
    echo "europarser service currently not running, starting gunicorn..."
    screen -S EuropressParser -dm bash -c "source /home/marceau/GH/EuropressParser/venv/bin/activate; python -m uvicorn europarser_api.api:app --port $EUROPARSER_PORT --root-path /europarser --workers 8 --limit-max-requests 8 --reload-dir /home/marceau/GH/EuropressParser --timeout-keep-alive 1000 --log-config log.conf"
else
    echo "europarser already running, restarting..."
    screen -S EuropressParser -X quit
    screen -S EuropressParser -dm bash -c "source /home/marceau/GH/EuropressParser/venv/bin/activate; python -m uvicorn europarser_api.api:app --port $EUROPARSER_PORT --root-path /europarser --workers 8 --limit-max-requests 8 --reload-dir /home/marceau/GH/EuropressParser --timeout-keep-alive 1000 --log-config log.conf"
fi
cd -
