VENV=.venv

.PHONY: venv test

venv:
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate; python -m pip install -q -r requirements.txt pytest

test:
	. $(VENV)/bin/activate; PYTHONPATH=. pytest --cov=jiraproject --cov-report=xml --cov-report=term -q


