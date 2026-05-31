.PHONY: install install-dev test lint scan sim-text

install:
	python3 -m pip install -e .

install-dev:
	python3 -m pip install -e .[dev]

test:
	pytest

lint:
	ruff check .

scan:
	open-idotmatrix scan

sim-text:
	open-idotmatrix simulate --text "open-idotmatrix" --save out/sim_text.png
