.PHONY: test dev_install build upload

dev_install:
	python3 -m venv .venv
	. .venv/bin/activate && \
	pip3 install --upgrade pyjvc
test:
	LOG_LEVEL=debug python -m unittest discover -s tests
