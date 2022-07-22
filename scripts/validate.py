#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import sys
from pathlib import Path

import jsonschema
from jsonschema.exceptions import best_match, ValidationError
from pyjexl.jexl import JEXL


class NestedRefResolver(jsonschema.RefResolver):
    """A custom ref resolver that handles bundled schema.

    This is the resolver used by Experimenter.
    """

    def __init__(self, schema):
        super().__init__(base_uri=None, referrer=None)

        if "$id" in schema:
            self.store[schema["$id"]] = schema

        if "$defs" in schema:
            for dfn in schema["$defs"].values():
                if "$id" in dfn:
                    self.store[dfn["$id"]] = dfn


# Create a jexl evaluator
EVALUATOR = JEXL()
EVALUATOR.add_binary_operator("intersect", 40, lambda x, y: set(x).intersection(y))
EVALUATOR.add_transform("bucketSample", lambda x, y, z, q: False)
EVALUATOR.add_transform("date", lambda x: 0)
EVALUATOR.add_transform("keys", lambda x: [])
EVALUATOR.add_transform("length", lambda x: 0)
EVALUATOR.add_transform("mapToProperty", lambda x, y: [])
EVALUATOR.add_transform("preferenceExists", lambda x: False)
EVALUATOR.add_transform("preferenceIsUserSet", lambda x: False)
EVALUATOR.add_transform("preferenceValue", lambda x: False)
EVALUATOR.add_transform("regExpMatch", lambda x: False)
EVALUATOR.add_transform("stableSample", lambda x, y: False)
EVALUATOR.add_transform("versionCompare", lambda x: 0)

# cache all the known schemas to validate experiments
ALL_SCHEMAS = dict()

SCHEMA_MAP = {
    "message": Path("schema", "MessagingExperiment.schema.json"),
    "experiment": Path("schema", "NimbusExperiment.schema.json"),
    "action": Path("schema", "SpecialMessageActionSchemas.json"),
    "message-groups": Path("schema", "message-groups.schema.json"),
}

USAGE = """
    Usage:
        validate.py TYPE PATH

    Where TYPE should be one of "message", "experiment", or "message-groups".

    Exmaple:
        validate.py message ./outgoing/cfr.json
"""


def load_schema(name):
    """Load a schema and cache it."""
    if name in ALL_SCHEMAS:
        return ALL_SCHEMAS[name]

    with SCHEMA_MAP[name].open("r") as f:
        schema = json.load(f)
        if name == "experiment":
            # The NimbusExperiment schema contains a self-ref.
            schema = {
                "$schema": schema["$schema"],
                **schema["definitions"]["NimbusExperiment"],
            }

        ALL_SCHEMAS[name] = schema

    return ALL_SCHEMAS[name]


def validate_item_targeting(item, for_exp=False):
    if "targeting" not in item and "filter_expression" not in item:
        return
    indentation = "\t" if for_exp else ""
    print("{}Validate targeting {}".format(indentation, item["id"]))
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
    """Validate a special message action"""
    indentation = "\t" if for_exp else ""
    schema = load_schema("action")

    print("{}Validate message action {}".format(indentation, action["type"]))

    try:
        jsonschema.validate(instance=action, schema=schema)
    except ValidationError as err:
        match = best_match([err])
        print("{}Validation error: {}".format(indentation, match.message))
        sys.exit(1)


def extract_actions(message):
    """Extract all of the special message actions from the given message."""
    message_type = message["template"]

    def _extract_cfr_doorhanger():
        buttons_prop = message["content"].get("buttons", {})
        if type(buttons_prop) is list:
            for button in buttons_prop:
                yield button["action"]
        else:
            for name, button in buttons_prop.items():
                if name == "primary":
                    yield button["action"]
                else:
                    for sub_button in button:
                        if "action" in sub_button:
                            yield sub_button["action"]

    def _extract_cfr_urlbar_chiclet():
        yield message["content"]["action"]

    def _extract_infobar():
        for button in message["buttons"]:
            yield button["action"]

    def _extract_spotlight():
        template = message["content"].get("template", "logo-and-content")

        if template == "logo-and-content":
            yield message["content"]["body"]["primary"]["action"]
            yield message["content"]["body"]["secondary"]["action"]
        elif template == "multistage":
            for screen in message["content"]["screens"]:
                for button_name in ["primary_button", "secondary_button"]:
                    button = screen["content"].get(button_name)
                    if button and button["action"].get("type"):
                        yield button["action"]

    def _extract_toolbar_badge():
        if "action" in message["content"]:
            yield message["content"]["action"]

    def _extract_pb_newtab():
        if "promoButton" in message["content"]:
            yield message["content"]["promoButton"]["action"]

    extractors = {
        "cfr_doorhanger": _extract_cfr_doorhanger,
        "cfr_urlbar_chiclet": _extract_cfr_urlbar_chiclet,
        "infobar": _extract_infobar,
        "spotlight": _extract_spotlight,
        "toolbar_badge": _extract_toolbar_badge,
        "pb_newtab": _extract_pb_newtab,
    }

    try:
        yield from extractors[message_type]()
    except KeyError:
        return []


def validate_all_actions(message, for_exp=False):
    """Validate all actions in the given message."""
    for action in extract_actions(message):
        validate_action(action, for_exp)


def get_branch_message(branch):
    """Return the message from an experiment branch."""
    # TODO: This does not support multi-feature experiments.
    feature = branch["feature"]
    feature_id = feature["featureId"]
    if feature_id == "cfr":
        value = feature["value"]
        if value is not None and "id" in value:
            return "cfr", feature["value"]
        return "cfr", None
    elif feature_id == "aboutwelcome":
        value = feature["value"]
        if value is None:
            return "onboarding-multistage", None
        elif "cards" in value:
            return "onboarding", value["cards"]
        elif "screens" in value:
            return "onboarding-multistage", value
        else:
            return "onboarding", None
    elif feature_id == "moments-page":
        if "id" in feature["value"]:
            return "moments-page", feature["value"]
        return "moments-page", None
    else:
        return None, None


def validate_experiment_message_id(exp_slug, branch):
    """This validation enforces certain naming convention for some message
    types such as CFR in order to support the automated analysis feature of
    Jetstream.
    """
    message_type, branch_message = get_branch_message(branch)
    if branch_message is None:
        return

    if message_type == "cfr":
        print(f"\tValidate experiment message ID for branch {branch['slug']}")

        assert branch_message["id"] == f"{exp_slug}:{branch['slug']}", (
            f"Invalid CFR message ID {branch_message['id']}, "
            f"it should be named as {{experiment-slug}}:{{branch-slug}}"
        )
        assert (
            branch_message["content"]["bucket_id"] == f"{exp_slug}:{branch['slug']}"
        ), (
            f"Invalid CFR bucket_id {branch_message['content']['bucket_id']}, "
            f"it should be named as {{experiment-slug}}:{{branch-slug}}"
        )


def validate_experiment(item):
    for branch in item.get("branches"):
        message_type, branch_message = get_branch_message(branch)
        if branch_message is None:
            print("\tSkip branch {} because it's empty".format(branch.get("slug")))
            continue

        schema = load_schema(message_type)
        try:
            branch_message_list = (
                branch_message if isinstance(branch_message, list) else [branch_message]
            )
            for message in branch_message_list:
                jsonschema.validate(instance=message, schema=schema)
            print(
                "\tValidate {} with schema {}".format(branch.get("slug"), message_type)
            )
        except ValidationError as err:
            match = best_match([err])
            print("\tValidation error: {}".format(match.message))
            sys.exit(1)

        # Validate the targeting JEXL if any
        validate_item_targeting(branch_message, True)

        # Validate all the message actions
        validate_all_actions(branch_message, True)

        # Validate the message_id naming
        validate_experiment_message_id(item["slug"], branch)


def validate_message(message):
    """Validate the components of a message"""
    validate_item_targeting(message)
    validate_all_actions(message)


def validate(schema_name, src_path):
    schema = load_schema(schema_name)
    resolver = NestedRefResolver(schema)

    print(f"Validating {src_path} with {schema_name} schema...")
    with open(src_path, "r") as f:
        items = json.load(f)

        if items is not None:
            for item in items:
                print(f"Valiating schema for {item['id']}")

                try:
                    jsonschema.validate(
                        instance=item,
                        schema=schema,
                        resolver=resolver,
                    )
                except ValidationError as err:
                    match = best_match([err])
                    print(f"Validation error: {match.message}")
                    sys.exit(1)

                if schema_name == "message":
                    validate_message(item)
                elif schema_name == "experiment":
                    validate_experiment(item)
                elif schema_name == "message-group":
                    pass
                elif schema_name == "action":
                    pass

    print("PASS")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)

    validate(sys.argv[1], sys.argv[2])
