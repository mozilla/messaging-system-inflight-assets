#!/bin/bash

PYTHON=python3
EXPERIMENTER_URL=https://experimenter.services.mozilla.com/api/v1/experiments
RECIPE_URL=${EXPERIMENTER_URL}/$1/recipe/

if [[ -z $1 ]]; then
  curl -SsL ${EXPERIMENTER_URL}/ | jq -r '.[].slug'
  echo "Choose from one of the available slugs: $0 [slug_name]"
else
  json_input=$(
    curl -SsL ${RECIPE_URL} |\
    jq -r '{id: .experimenter_slug, enabled: true, arguments: .arguments, filter_expression: "", targeting: ""}'
  )
  ${PYTHON} -c 'import sys, yaml, json; yaml.dump(json.load(sys.stdin), sys.stdout)
    '<<<${json_input} > $1.yaml
fi
