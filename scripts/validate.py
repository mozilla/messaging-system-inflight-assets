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

# cache all the known schemas to validate experiments
ALL_SCHEMAS = dict()

USAGE = """
    Usage:
        validate.py ${JSON_PATH} ${SCHEMA_PATH}

    Exmaple:
        validate.py ./cfr.json ./schema/cfr.schema.json
"""


def validate_item_targeting(item, for_exp=False):
    if "targeting" not in item and "filter_expression" not in item:
        return
    indentation = "\t" if for_exp else ""
    print("{}Validate targeting {}".format(indentation, item['id']))
    for key in ["targeting", "filter_expression"]:
        jexl_expression = item.get(key)
        if jexl_expression is None:
            continue
        try:
            result = list(EVALUATOR.validate(jexl_expression))
            if len(result) > 0:
                raise Exception(result[0])
        except Exception as e:
            print(e)
            sys.exit(1)


def load_all_schemas():
    if len(ALL_SCHEMAS):
        return

    possible_schemas = [
        "schema/cfr.schema.json",
        "schema/onboarding.schema.json",
        "schema/cfr-fxa.schema.json",
        "schema/cfr-heartbeat.schema.json",
        "schema/messaging-experiments.schema.json",
        "schema/whats-new-panel.schema.json",
    ]
    for path in possible_schemas:
        with open(path, "r") as f:
            ALL_SCHEMAS[path] = json.loads(f.read())


def get_branch_message(branch_value):
    if "id" in branch_value:
        # CFR messages
        return branch_value
    if "cards" in branch_value:
        # Onboarding messages
        return branch_value.get("cards")

    return None


def validate_experiment(item):
    # Load all the schemas to validate experiment messages
    load_all_schemas()

    validated = 0
    for branch in item.get("arguments").get("branches"):
        branch_message = get_branch_message(branch.get("value"))
        if branch_message is None:
            print("\tSkip branch {} because it's empty".format(branch.get("slug")))
            validated += 1
            continue
        # Try all of the available message schemas
        for schema_path in ALL_SCHEMAS.keys():
            try:
                branch_message_list = branch_message if isinstance(branch_message, list) else [branch_message]
                for message in branch_message_list:
                    jsonschema.validate(instance=message, schema=ALL_SCHEMAS.get(schema_path))
                validated += 1
                print("\tValidated {} with {}".format(branch.get("slug"), schema_path))
                break
            except ValidationError as err:
                match = best_match([err])
                print("\tValidation error: {}".format(match.message))
                print("\tTried to validate {} with {}\n".format(branch.get("slug"), schema_path))

        # Validate the targeting JEXL if any
        validate_item_targeting(branch_message, True)

    if validated != len(item.get("arguments").get("branches")):
        print("\tBranches did not validate for {}".format(item.get("id")))
        sys.exit(1)


def validate(src_path, schema_path):
    with open(schema_path, "r") as f:
        schema = json.loads(f.read())

    with open(src_path, "r") as f:
        items = json.loads(f.read())
        for item in items:
            try:
                jsonschema.validate(instance=item, schema=schema)
                # If it's an experiment we want to evaluate the branches
                if "arguments" in item:
                    validate_experiment(item)
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
