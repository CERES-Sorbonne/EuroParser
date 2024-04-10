#!/usr/bin/env bash

set -efaou pipefail

source .env_europarser > /dev/null 2>&1

set +a

set +ue
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
set -ue

cd "${FOLDER:=`pwd`/}"

# Ensure pwd has worked
if [ -z "${FOLDER%/*}" ]
then
    echo "The pwd command failed, leading to cd to $FOLDER"
    exit 1
fi

# git pull origin master --quiet || exit


if [ ! -d "venv" ]
then
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

source "$FOLDER"/"venv/bin/activate"

set +e
sed "s/\(.*\)\(--\|#\).*/\1/g" "requirements.txt" | grep -v '^ *#' | while IFS= read -r package
do
    if [[ "git" == *"$package"* ]]
    then
      package_name=$(echo "$package" | cut -d'@' -f1)
      package_url=$(echo "$package" | cut -d'@' -f2)
      if ! pip show "$package_name" > /dev/null
      then
          echo "Missing $package, trying to install it..."
          pip install git+"$package_url"@master
      fi
    else
      if ! pip show "$package" > /dev/null
      then
          echo "Missing $package, trying to install it..."
          pip install "$package"
      fi
    fi
done
set -e

COMMAND="source $FOLDER/venv/bin/activate; python -m uvicorn src.europarser.api.api:app --host ${EUROPARSER_HOST:-'0.0.0.0'} --port ${EUROPARSER_PORT:-'8000'} --root-path ${ROOT_PATH:-'/'} --workers 8 --timeout-keep-alive 1000 --log-config log.conf"

printf "Starting europarser with command:\n"
echo "$COMMAND"

set +ue
IS_RUNNING=$(ps -aux | grep uvicorn | grep europarser_api)
if [ -z "$IS_RUNNING" ]
then
    set -ue
    echo "europarser service currently not running, starting gunicorn..."
    screen -S EuropressParser -dm bash -c "$COMMAND"
else
    set -ue
    echo "europarser already running, restarting..."
    screen -S EuropressParser -X quit
    screen -S EuropressParser -dm bash -c "$COMMAND"
fi

cd -
