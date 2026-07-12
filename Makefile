.PHONY: test docs build

test:
	uv run pytest --cov=tafor --cov-report=term --cov-report=html

docs:
	uv run sphinx-build -b html docs docs/_build/html

build:
	uv run python build.py
