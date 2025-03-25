PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: outgoing/cfr-heartbeat.json outgoing/cfr.json \
     outgoing/message-groups.json outgoing/messaging-experiments.json \
     outgoing/moments.json outgoing/whats-new-panel.json

outgoing/%.json: messages/%.yaml pre-build
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

.PHONY: clean check

pre-build:
	yamllint .

clean:
	rm *.json

check:
	scripts/validate.py message outgoing/cfr.json
	scripts/validate.py message outgoing/cfr-heartbeat.json
	scripts/validate.py message outgoing/moments.json
	scripts/validate.py message outgoing/whats-new-panel.json
	scripts/validate.py experiment outgoing/messaging-experiments.json
	scripts/validate.py message-groups outgoing/message-groups.json

export: all
	scripts/export-all.py
