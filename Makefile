.PHONY: setup install install-dev update clean test format lint lint-fix doc type all-checks

# Default target executed when no arguments are given to make.
default: help

# Define standard colors
BLACK        := $(shell tput -Txterm setaf 0)
RED          := $(shell tput -Txterm setaf 1)
GREEN        := $(shell tput -Txterm setaf 2)
YELLOW       := $(shell tput -Txterm setaf 3)
BLUE         := $(shell tput -Txterm setaf 4)
MAGENTA      := $(shell tput -Txterm setaf 5)
CYAN         := $(shell tput -Txterm setaf 6)
WHITE        := $(shell tput -Txterm setaf 7)
RESET        := $(shell tput -Txterm sgr0)

# Target for displaying help
help:
	@echo "$(GREEN)Available targets:$(RESET)"
	@echo "$(YELLOW)setup$(RESET)        : Setup development environment (install dependencies and pre-commit hooks)"
	@echo "$(YELLOW)install$(RESET)      : Install the package in the current Python environment"
	@echo "$(YELLOW)install-dev$(RESET)  : Install the package with development dependencies"
	@echo "$(YELLOW)update$(RESET)       : Update dependencies and tools to latest versions"
	@echo "$(YELLOW)clean$(RESET)        : Clean build artifacts"
	@echo "$(YELLOW)test$(RESET)         : Run tests"
	@echo "$(YELLOW)format$(RESET)       : Format code"
	@echo "$(YELLOW)lint$(RESET)         : Run linting checks"
	@echo "$(YELLOW)lint-fix$(RESET)     : Run linters with auto-fix option"
	@echo "$(YELLOW)doc$(RESET)          : Check documentation coverage"
	@echo "$(YELLOW)type$(RESET)         : Run type checking"
	@echo "$(YELLOW)all-checks$(RESET)   : Run all checks (lint, type, doc, test)"

# Setup the development environment
setup:
	@echo "$(BLUE)Setting up development environment...$(RESET)"
	poetry install
	pre-commit install
	@echo "$(GREEN)Development environment set up successfully.$(RESET)"

# Install package
install:
	@echo "$(BLUE)Installing package...$(RESET)"
	poetry install --no-dev
	@echo "$(GREEN)Package installed successfully.$(RESET)"

# Install package with development dependencies
install-dev:
	@echo "$(BLUE)Installing package with development dependencies...$(RESET)"
	poetry install
	@echo "$(GREEN)Package installed successfully with development dependencies.$(RESET)"

# Update dependencies and tools
update:
	@echo "$(BLUE)Updating dependencies and tools...$(RESET)"
	python scripts/update_environment.py
	@echo "$(GREEN)Environment updated successfully.$(RESET)"

# Clean build artifacts
clean:
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@echo "$(GREEN)Cleaned build artifacts successfully.$(RESET)"

# Run tests
test:
	@echo "$(BLUE)Running tests...$(RESET)"
	poetry run pytest
	@echo "$(GREEN)Tests executed successfully.$(RESET)"

# Format code
format:
	@echo "$(BLUE)Formatting code...$(RESET)"
	poetry run ruff format .
	@echo "$(GREEN)Code formatted successfully.$(RESET)"

# Run linting
lint:
	@echo "$(BLUE)Running linting checks...$(RESET)"
	poetry run ruff check .
	@echo "$(GREEN)Linting checks completed.$(RESET)"

# Run linting with auto-fix
lint-fix:
	@echo "$(BLUE)Running linting with auto-fix...$(RESET)"
	poetry run ruff check --fix .
	@echo "$(GREEN)Linting with auto-fix completed.$(RESET)"

# Check documentation coverage
doc:
	@echo "$(BLUE)Checking documentation coverage...$(RESET)"
	poetry run interrogate -c pyproject.toml ztoq/
	@echo "$(GREEN)Documentation coverage check completed.$(RESET)"

# Run type checking
type:
	@echo "$(BLUE)Running type checking...$(RESET)"
	poetry run mypy ztoq/
	@echo "$(GREEN)Type checking completed.$(RESET)"

# Run all checks
all-checks: lint type doc test
	@echo "$(GREEN)All checks completed successfully.$(RESET)"
