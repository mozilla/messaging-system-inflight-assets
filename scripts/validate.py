#!/usr/bin/env python3

import json
import sys

import jsonschema

from jsonschema.exceptions import best_match, ValidationError
from pyjexl.jexl import JEXL

# Create a jexl evaluator
EVALUATOR = JEXL()
EVALUATOR.add_binary_operator('intersect', 40, lambda x, y: set(x).intersection(y))
EVALUATOR.add_transform('date', lambda x: 0)
EVALUATOR.add_transform('length', lambda x: 0)
EVALUATOR.add_transform('preferenceValue', lambda x: False)
EVALUATOR.add_transform('mapToProperty', lambda x, y: [])
EVALUATOR.add_transform('keys', lambda x: [])
EVALUATOR.add_transform('bucketSample', lambda x, y, z, q: False)
EVALUATOR.add_transform('stableSample', lambda x, y: False)

USAGE = """
    Usage:
        validate.py ${JSON_PATH} ${SCHEMA_PATH}

    Exmaple:
        validate.py ./cfr.json ./schema/cfr.schema.json
"""


def validate_item_targeting(item):
    print("Validate", item['id'])
    jexl_expression = item.get("targeting") or item.get("filter_expression")
    try:
        result = list(EVALUATOR.validate(jexl_expression))
        if len(result) > 0:
            raise Exception(result[0])
    except Exception as e:
        print(e)
        sys.exit(1)


def validate(src_path, schema_path):
    with open(schema_path, "r") as f:
        schema = json.loads(f.read())

    with open(src_path, "r") as f:
        items = json.loads(f.read())
        for item in items:
            try:
                jsonschema.validate(instance=item, schema=schema)
            except ValidationError as err:
                match = best_match([err])
                print("Validation error: {}".format(match.message))
                sys.exit(1)
            validate_item_targeting(item)

    print("Passed!")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)

    validate(sys.argv[1], sys.argv[2])
