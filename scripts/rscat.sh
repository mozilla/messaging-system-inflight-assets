#!/bin/bash

USAGE="Usage:

# list all collections
$0

# list all record IDs in a collection
$0 -l collection-name

# list all records in a collection
$0 collection-name

# list a specific record in a collection
$0 -r record-name collection-name
"

RS_URL=https://firefox.settings.services.mozilla.com/v1/buckets/main/collections

POSTIONAL=()
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -l|--list)
            list=YES
            shift
            ;;
        -r|--record)
            record="$2"
            shift
            shift
            ;;
        -h|--help)
            echo "${USAGE}"
            exit 0
            ;;
        *)
            POSTIONAL+=("$1")
            shift
            ;;
    esac
done

if [[ ${#POSTIONAL[@]} -eq 0 ]]; then
    curl -SsL ${RS_URL} | jq -r '.data | .[].id'
    exit 0
fi

collection=${POSTIONAL[0]}

RS_FULL_URL=${RS_URL}/${collection}/records

if [[ -z ${record} ]]; then
    if [[ "${list}" == YES ]]; then
        curl -SsL ${RS_FULL_URL} | jq -r '.data | .[].id'
    else
        curl -SsL ${RS_FULL_URL} | jq -r '.data | .[]'
    fi
else
    curl -SsL ${RS_FULL_URL} | jq -r --arg r "${record}" '.data | .[] | select(.id == $r)'
fi
