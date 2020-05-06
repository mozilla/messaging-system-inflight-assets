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
    possible_schemas = ["./schema/cfr.schema.json"]

    with open(schema_path, "r") as f:
        schema = json.loads(f.read())

    with open(src_path, "r") as f:
        items = json.loads(f.read())
        for item in items:
            try:
                jsonschema.validate(instance=item, schema=schema)
                # If it's an experiment we want to evaluate the branches
                if "arguments" in item:
                    validated = 0
                    for branch in item.get("arguments").get("branches"):
                        if "id" not in branch.get("value"):
                            print("\tSkip branch", branch.get("slug"))
                            validated = validated + 1
                            continue
                        # Try all of the available message schemas
                        for try_schema_path in possible_schemas:
                            with open(try_schema_path, "r") as sf:
                                message_schema = json.loads(sf.read())
                                try:
                                    jsonschema.validate(instance=branch.get("value"), schema=message_schema)
                                    validated = validated + 1
                                    print("\tValidated", branch.get("value").get("id"), "with", try_schema_path)
                                except ValidationError as err:
                                    match = best_match([err])
                                    print("Validation error: {}".format(match.message))
                                    print("\tTried to validate", branch.get("value").get("id"), "with", try_schema_path)
                    if validated != len(item.get("arguments").get("branches")):
                        print("Branches did not validate for", item.get("id"))
                        sys.exit(1)
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
