#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pathlib import Path

import requests

URL_BASE = "https://hg.mozilla.org/mozilla-central/raw-file/tip/"

SCHEMAS = {
    # The combined FxMS Mega schema
    "MessagingExperiment.schema.json": (
        "browser/components/newtab/content-src/asrouter/schemas/"
        "MessagingExperiment.schema.json"
    ),
    # The Nimbus recipe schema
    "NimbusExperiment.schema.json": (
        "toolkit/components/nimbus/schemas/NimbusExperiment.schema.json"
    ),
    # Non-message schemas
    "SpecialMessageActionSchemas.json": (
        "toolkit/components/messaging-system/schemas/"
        "SpecialMessageActionSchemas/SpecialMessageActionSchemas.json"
    ),
    "message-groups.schema.json": (
        "browser/components/newtab/content-src/asrouter/schemas/"
        "message-group.schema.json"
    ),
}


def main():
    session = requests.session()

    for schema, fragment in SCHEMAS.items():
        path = Path("schema") / schema
        url = URL_BASE + fragment

        print(f"Fetching {schema} ...")

        with path.open("w") as f, session.get(url) as req:
            f.write(req.text)


if __name__ == "__main__":
    main()
