#!/usr/bin/env python3

import json
import sys

import jsonschema

from jsonschema.exceptions import best_match, ValidationError
from pyjexl.jexl import JEXL

# Create a jexl evaluator
EVALUATOR = JEXL()
EVALUATOR.add_binary_operator(
    'intersect', 40, lambda x, y: set(x).intersection(y))
EVALUATOR.add_transform('date', lambda x: 0)
EVALUATOR.add_transform('length', lambda x: 0)
EVALUATOR.add_transform('preferenceValue', lambda x: False)
EVALUATOR.add_transform('mapToProperty', lambda x, y: [])
EVALUATOR.add_transform('keys', lambda x: [])
EVALUATOR.add_transform('bucketSample', lambda x, y, z, q: False)
EVALUATOR.add_transform('stableSample', lambda x, y: False)

# cache all the known schemas to validate experiments
ALL_SCHEMAS = dict()

SCHEMA_MAP = {
    "cfr": "schema/cfr.schema.json",
    "onboarding": "schema/onboarding.schema.json",
    "onboarding-multistage": "schema/onboarding-multistage.schema.json",
    "cfr-fxa": "schema/cfr-fxa.schema.json",
    "cfr-heartbeat": "schema/cfr-heartbeat.schema.json",
    "messaging-experiments": "schema/messaging-experiments.schema.json",
    "messaging-experiments-82": "schema/messaging-experiments-82.schema.json",
    "whats-new-panel": "schema/whats-new-panel.schema.json",
    "action": "schema/messaging-system-special-message-actions.schema.json",
    "message-groups": "schema/message-groups.schema.json",
    "moments-page": "schema/moments-action.schema.json",
}

USAGE = """
    Usage:

        validate.py ${TYPE} ${JSON_PATH}

    Where ${type} should be one of "cfr" "cfr-fxa", "messaging-experiments",
    "whats-new-panel".

    Exmaple:
        validate.py cfr ./cfr.json
"""


def load_schema(name):
    if name in ALL_SCHEMAS:
        return ALL_SCHEMAS[name]

    path = SCHEMA_MAP[name]
    with open(path, "r") as f:
        ALL_SCHEMAS[name] = json.loads(f.read())
    return ALL_SCHEMAS[name]


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
                raise SyntaxError(result[0])
        except SyntaxError as e:
            print(e)
            sys.exit(1)


def validate_action(action, for_exp):
    indentation = "\t" if for_exp else ""
    all_action_schemas = load_schema("action")
    action_type = action["type"]

    print("{}Validate message action {}".format(indentation, action_type))
    if action_type not in all_action_schemas:
        print("{}Unknown action {}".format(indentation, action_type))
        sys.exit(1)

    schema = all_action_schemas[action_type]
    try:
        jsonschema.validate(instance=action, schema=schema)
    except ValidationError as err:
        match = best_match([err])
        print("{}Validation error: {}".format(indentation, match.message))
        sys.exit(1)


def extract_actions(message, message_type):
    def _extract_cfr():
        for name, button in message["content"].get("buttons", {}).items():
            if name == "primary":
                yield button["action"]
            else:
                for sub_button in button:
                    if "action" in sub_button:
                        yield sub_button["action"]

    def _extract_onboarding():
        for card in message:
            button = card["content"]["primary_button"]
            if "action" in button:
                yield button["action"]

    def _extract_onboarding_multistage():
        for screen in message["screens"]:
            for button_name in ["primary_button", "secondary_button"]:
                button = screen["content"].get(button_name)
                if button and button["action"].get("type"):
                    yield button["action"]

    if message_type == "cfr":
        yield from _extract_cfr()
    elif message_type == "onboarding":
        yield from _extract_onboarding()
    elif message_type == "onboarding-multistage":
        yield from _extract_onboarding_multistage()
    elif message_type == "moments-page":
        # No actions to validate for moments-page
        return
    else:
        raise KeyError("invalid message type {}".format(message_type))


def validate_all_actions(message, message_type, for_exp=False):
    for action in extract_actions(message, message_type):
        validate_action(action, for_exp)


def get_branch_message(branch):
    if branch["groups"] == ["cfr"]:
        value = branch["value"]
        if "id" in value:
            return "cfr", branch["value"]
        return "cfr", None
    elif branch["groups"] == ["aboutwelcome"]:
        value = branch["value"]
        if value is None:
            return "onboarding-multistage", None
        elif "cards" in value:
            return "onboarding", value["cards"]
        elif "screens" in value:
            return "onboarding-multistage", value
        else:
            return "onboarding", None
    elif branch["groups"] == ["moments-page"]:
        if "id" in branch["value"]:
            return "moments-page", branch["value"]
        return "moments-page", None
    else:
        return None, None


def validate_experiment(item):
    for branch in item.get("arguments").get("branches"):
        message_type, branch_message = get_branch_message(branch)
        if branch_message is None:
            print(
                "\tSkip branch {} because it's empty"
                .format(branch.get("slug"))
            )
            continue

        schema = load_schema(message_type)
        try:
            branch_message_list = \
                branch_message if isinstance(branch_message, list) else [
                    branch_message]
            for message in branch_message_list:
                jsonschema.validate(instance=message, schema=schema)
            print("\tValidated {} with schema {}".format(
                branch.get("slug"), message_type))
        except ValidationError as err:
            match = best_match([err])
            print("\tValidation error: {}".format(match.message))
            sys.exit(1)

        # Validate the targeting JEXL if any
        validate_item_targeting(branch_message, True)

        # Validate all the message actions
        validate_all_actions(branch_message, message_type, True)


def validate(schema_name, src_path):
    schema = load_schema(schema_name)
    new_experiments_schema = load_schema("messaging-experiments-82")
    check_action = schema_name in ['cfr']

    with open(src_path, "r") as f:
        items = json.loads(f.read())
        for item in items:
            try:
                print("Validate schema for {}".format(item["id"]))
                if "arguments" in item:
                    try:
                        print("Validate {} with Experiments schema 82+".format(item["id"]))
                        jsonschema.validate(instance=item, schema=new_experiments_schema)
                    except ValidationError as err:
                        match = best_match([err])
                        print("Validation error against the new experiments schema: {}"
                              .format(match.message))
                        jsonschema.validate(instance=item, schema=schema)
                    # If it's an experiment we want to evaluate the branches
                    validate_experiment(item)
                else:
                    jsonschema.validate(instance=item, schema=schema)
            except ValidationError as err:
                match = best_match([err])
                print("Validation error: {}".format(match.message))
                sys.exit(1)
            validate_item_targeting(item)
            if check_action:
                validate_all_actions(item, schema_name)

    print("Passed!")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)

    validate(sys.argv[1], sys.argv[2])
