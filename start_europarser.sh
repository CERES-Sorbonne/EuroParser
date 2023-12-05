#!/bin/bash

source .env_europarser > /dev/null 2>&1

if [ "$EUROPARSER_OUTPUT" ]
then
    echo "EUROPARSER_OUTPUT is set to '$EUROPARSER_OUTPUT'"
else
    echo "EUROPARSER_OUTPUT is not set, if you continue, no output will be saved"
    read -p "Continue? [y/N] " -n 1 -r < /dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        echo "Aborting"
        exit 1
    else
        echo "Caution, no output will be saved"
    fi
fi


export EUROPARSER_SERVER=https://ceres.huma-num.fr/europarser
export EUROPARSER_PORT=8001
export FOLDER=/home/marceau/GH/EuropressParser

cd $FOLDER || exit

git pull origin master --quiet || exit

python3.11 -m venv venv
source $FOLDER/venv/bin/activate || exit
pip3 install -U pip --quiet || exit
pip3 install -r $FOLDER/requirements.txt --quiet || exit
pip3 install -r $FOLDER/requirements-api.txt --quiet || exit

IS_RUNNING=$(ps -aux | grep uvicorn | grep europarser_api)
if [ -z "$IS_RUNNING" ]
then
    echo "europarser service currently not running, starting gunicorn..."
    screen -S EuropressParser -dm bash -c "source /home/marceau/GH/EuropressParser/venv/bin/activate; python -m uvicorn europarser_api.api:app --port $EUROPARSER_PORT --root-path /europarser --workers 8 --limit-max-requests 8 --timeout-keep-alive 1000 --log-config log.conf"
else
    echo "europarser already running, restarting..."
    screen -S EuropressParser -X quit
    screen -S EuropressParser -dm bash -c "source /home/marceau/GH/EuropressParser/venv/bin/activate; python -m uvicorn europarser_api.api:app --port $EUROPARSER_PORT --root-path /europarser --workers 8 --limit-max-requests 8 --timeout-keep-alive 1000 --log-config log.conf"
fi
cd -
