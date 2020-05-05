PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: cfr.json cfr-fxa.json cfr-heartbeat.json whats-new-panel.json messaging-experiments.json 

%.json:%.yaml pre-build
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

.PHONY: clean check

pre-build:
	yamllint .

clean:
	rm *.json

check:
	scripts/validate.py cfr.json schema/cfr.schema.json
	scripts/validate.py cfr-fxa.json schema/cfr-fxa.schema.json
	scripts/validate.py whats-new-panel.json schema/whats-new-panel.schema.json
	scripts/validate.py messaging-experiments.json schema/messaging-experiments.schema.json
