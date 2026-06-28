.PHONY: install lint format typecheck test check clean

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy src

test:
	pytest

# Everything CI runs, in one command -- run this before opening a PR.
check: lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
