.DEFAULT_GOAL := ui

.PHONY: test docs build ui

test:
	uv run pytest --cov=tafor --cov-report=term --cov-report=html

docs:
	uv run sphinx-build -b html docs docs/_build/html

build:
	uv run python build.py

UI_SRCS := $(wildcard tafor/ui/qt/*.ui)
UI_GENS := $(patsubst tafor/ui/qt/%.ui,tafor/ui/qt/Ui_%.py,$(UI_SRCS))

ui: $(UI_GENS)

tafor/ui/qt/Ui_%.py: tafor/ui/qt/%.ui
	uv run pyuic5 -o $@ $<
