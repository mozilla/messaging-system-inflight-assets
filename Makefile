PYTHON = python3
FLAGS = -c
CMD = 'import sys, yaml, json; json.dump(yaml.load(sys.stdin, Loader=yaml.Loader), sys.stdout, indent=2)'

all: cfr.json cfr-fxa.json whats-new-panel.json whats-new-panel-archived.json

%.json:%.yaml
	$(PYTHON) $(FLAGS) $(CMD) < $< > $@

.PHONY: clean

clean:
	rm *.json
