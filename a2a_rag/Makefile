PYTHON := .venv/bin/python

.PHONY: check test run

check:
	$(PYTHON) -m py_compile *.py

test:
	$(PYTHON) -m unittest discover -v

run:
	$(PYTHON) policy_server.py
