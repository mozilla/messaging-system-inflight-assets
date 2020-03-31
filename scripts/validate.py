#!/usr/bin/env python3

import json
import sys

import jsonschema


USAGE = """
    Usage:
        validate.py ${JSON_PATH} ${SCHEMA_PATH}

    Exmaple:
        validate.py ./cfr.json ./schema/cfr.schema.json
"""


def validate(src_path, schema_path):
    with open(schema_path, "r") as f:
        schema = json.loads(f.read())

    with open(src_path, "r") as f:
        items = json.loads(f.read())
        for item in items:
            jsonschema.validate(instance=item, schema=schema)

    print("Passed!")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)

    validate(sys.argv[1], sys.argv[2])
