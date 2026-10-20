PYTHON := .venv/bin/python
UV := uv
REQUIREMENTS := requirements.txt
SERVER := loan_closure_a2a_server.py

.PHONY: install run check

install:
	$(UV) pip install --python $(PYTHON) -r $(REQUIREMENTS)

run:
	$(PYTHON) $(SERVER)

check:
	$(PYTHON) -m py_compile *.py
