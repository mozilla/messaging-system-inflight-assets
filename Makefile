PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: cfr.json cfr-fxa.json cfr-heartbeat.json whats-new-panel.json messaging-experiments.json message-groups.json

%.json:%.yaml pre-build
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

.PHONY: clean check

pre-build:
	yamllint .

clean:
	rm *.json

check:
	scripts/validate.py cfr cfr.json
	scripts/validate.py cfr-fxa cfr-fxa.json
	scripts/validate.py whats-new-panel whats-new-panel.json
	scripts/validate.py messaging-experiments messaging-experiments.json
	scripts/validate.py message-groups message-groups.json
