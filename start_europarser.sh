#!/bin/bash

set -a
source .env_europarser > /dev/null 2>&1

if [ "$EUROPARSER_OUTPUT" ]
then
    echo "EUROPARSER_OUTPUT is set to '$EUROPARSER_OUTPUT'"
else
    echo "EUROPARSER_OUTPUT is not set, if you continue, no output will be saved"
    read -p "Continue? [ y / $(tput setaf 1)N$(tput sgr0) ] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        echo "Aborting"
        exit 1
    else
        echo "Caution, no output will be saved"
    fi
fi

set +a

cd $FOLDER || exit

git pull origin master --quiet || exit

if [ ! -d "venv" ]
then
    python3.11 -m venv venv || exit
    pip install . || exit
fi
source $FOLDER/venv/bin/activate || exit

COMMAND="source $FOLDER/venv/bin/activate; python -m uvicorn src.europarser.api.api:app --host 0.0.0.0 --port $EUROPARSER_PORT --root-path $ROOT_PATH --workers 8 --limit-max-requests 8 --timeout-keep-alive 1000 --log-config log.conf"
printf "Starting europarser with command:\n"
echo "$COMMAND"

IS_RUNNING=$(ps -aux | grep uvicorn | grep europarser_api)
if [ -z "$IS_RUNNING" ]
then
    echo "europarser service currently not running, starting gunicorn..."
    screen -S EuropressParser -dm bash -c "$COMMAND"
else
    echo "europarser already running, restarting..."
    screen -S EuropressParser -X quit
    screen -S EuropressParser -dm bash -c "$COMMAND"
fi

cd -
