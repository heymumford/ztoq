# Makefile for ZTOQ project

.PHONY: setup install test lint format clean docs docs-clean

setup:
	pip install poetry
	poetry install

install:
	poetry install

test:
	poetry run pytest

test-unit:
	poetry run pytest -m unit

test-integration:
	poetry run pytest -m integration

test-cov:
	poetry run pytest --cov=ztoq --cov-report=term --cov-report=html

lint:
	poetry run flake8 ztoq tests

format:
	poetry run black ztoq tests

validate:
	poetry run ztoq validate z-openapi.yml

list-endpoints:
	poetry run ztoq list-endpoints z-openapi.yml

docs:
	cd docs/sphinx && make html

docs-clean:
	cd docs/sphinx && make clean

docs-serve: docs
	cd docs/sphinx/build/html && python -m http.server 8000

# Generate API documentation automatically
apidoc:
	sphinx-apidoc -o docs/sphinx/source/api ztoq

# Build documentation after running tests with coverage
test-with-docs: test-cov docs

clean:
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf __pycache__
	rm -rf **/__pycache__
	rm -rf *.egg-info
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf docs/sphinx/build
