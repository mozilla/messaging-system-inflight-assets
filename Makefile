PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: cfr.json cfr-archived.json cfr-fxa.json cfr-fxa-archived.json whats-new-panel.json whats-new-panel-archived.json

%.json:%.yaml pre-build
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

pre-build:
	yamllint .

.PHONY: clean check

clean:
	rm *.json

check:
	scripts/validate.py cfr.json schema/cfr.schema.json
	scripts/validate.py cfr-fxa.json schema/cfr-fxa.schema.json
	scripts/validate.py whats-new-panel.json schema/whats-new-panel.schema.json
