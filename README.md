[![Mozilla](https://circleci.com/gh/mozilla/messaging-system-inflight-assets.svg?style=svg)](https://circleci.com/gh/mozilla/messaging-system-inflight-assets)

This repo hosts various in-flight remote assets of Firefox Messaging System.

Currently, it consists of CFR, CFR-FXA, and What's New Pannel.

### Usage

To add/modify/delete assets, please edit the YAML files other than the JSON ones, because the former allows us to use comments in the document. Once you complete the editing, you can sync your changes to the JSON file(s), and copy them over to Remote Settings for publishing.

When deleting asset(s), make sure copy the deleted content in the YAML files to the corresponding archive file located in the `archive` directory. For instance, when you're deleting messages in `cfr.yaml`, please copy the deletions to the `archive/cfr-archived.yaml`.

To sync from YAML to JSON, just run

```sh
$ make
```

To validate the JSON against the schema

```sh
$ make check
```

It requires Python 3 and various libraries for the schema validation and file generation.

```sh
# if you don't have Python 3 installed
$ brew install python3
$ pip3 install -r requirements.txt
```

Note: make sure you commit all the changes (YAML&JSON) to the repo.
