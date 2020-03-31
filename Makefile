PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: cfr.json cfr-archived.json cfr-fxa.json cfr-fxa-archived.json whats-new-panel.json whats-new-panel-archived.json

%.json:%.yaml pre-build
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

pre-build:
	yamllint .

.PHONY: clean

clean:
	rm *.json
