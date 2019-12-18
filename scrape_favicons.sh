#!/bin/bash

BANG_FILE=".bangs-cache/bang.js"
FAV_DIR=".favs"

mkdir -p $FAV_DIR

mapfile -t domains < <(jq -r '.[].d'  < $BANG_FILE)
for domain in "${domains[@]}"; do
    ICO_FILENAME="$FAV_DIR/$domain.ico"
    URL="$domain/favicon.ico"
    if [ ! -f $ICO_FILENAME ]; then
        echo "get from $URL"
        curl "$URL" -L -m 10 -s -o $ICO_FILENAME
    else
        identify $ICO_FILENAME &> /dev/null 
        if [[ $? != 0 ]]; then
            echo "bad image $URL"
            curl "$URL" -L -m 10 -s -o $ICO_FILENAME
        fi
    fi
done