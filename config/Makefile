# Makefile for ZTOQ project

.PHONY: setup install test lint lint-strict format clean docs docs-clean build checkin security pre-commit docker-build docker-run validate-all test-unit test-integration test-docker test-docker-no-containers docstring-check

setup:
	pip install poetry
	poetry install
	poetry run pre-commit install

install:
	poetry install

test:
	poetry run pytest

test-unit:
	poetry run pytest -m unit

test-integration:
	poetry run pytest -m integration

test-docker:
	poetry run pytest -m docker

test-docker-no-containers:
	SKIP_DOCKER_TESTS=1 poetry run pytest -m docker

test-cov:
	poetry run pytest --cov=ztoq --cov-report=term --cov-report=html --cov-report=xml

lint:
	poetry run ruff check .
	poetry run mypy ztoq
	poetry run interrogate -c pyproject.toml ztoq
	poetry run bandit -c pyproject.toml -r ztoq

lint-strict:
	poetry run ruff check .
	poetry run mypy ztoq
	poetry run interrogate -c pyproject.toml ztoq
	poetry run bandit -c pyproject.toml -r ztoq
	poetry run pylint ztoq

format:
	poetry run ruff format .
	poetry run ruff check --fix .
	poetry run isort .
	poetry run docformatter --in-place --config ./pyproject.toml ztoq

security:
	poetry run bandit -r ztoq -c pyproject.toml
	poetry run safety check
	
docstring-check:
	poetry run interrogate -v -c pyproject.toml ztoq

pre-commit:
	poetry run pre-commit run --all-files

docker-build:
	docker build -t ztoq:latest .

docker-run:
	docker run --rm -it ztoq:latest

validate-all: format lint test-cov security docstring-check

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

build:
	python scripts/master_build.py

checkin:
	@if [ -z "$(message)" ]; then \
		echo "Error: Commit message required. Usage: make checkin message=\"Your commit message\""; \
		exit 1; \
	fi
	python scripts/check_in.py "$(message)"

clean:
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf __pycache__
	rm -rf **/__pycache__
	rm -rf *.egg-info
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf docs/sphinx/build

docker-build:
	docker build -t ztoq:latest .

docker-run:
	docker run --rm -it ztoq:latest
