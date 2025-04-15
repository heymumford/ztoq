"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Validation integration module for connecting the validation framework with the migration process.

This module provides the integration layer between the migration process and the validation
framework, ensuring that validation rules are applied at the appropriate phases of migration.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Type, TypeVar
from ztoq.validation import (
    MigrationRetryHandler,
    MigrationValidator,
    RetryPolicy,
    ValidationIssue,
    ValidationLevel,
    ValidationManager,
    ValidationPhase,
    ValidationRule,
    ValidationScope,
)
from ztoq.validation_rules import get_built_in_rules

logger = logging.getLogger("ztoq.validation_integration")

# Type variable for generic function signatures
T = TypeVar("T")


class MigrationValidationDecorators:
    """Provides decorators for adding validation to migration methods."""

    def __init__(
        self, validation_manager: ValidationManager, retry_handler: MigrationRetryHandler = None
    ):
        """
        Initialize the decorator provider.

        Args:
            validation_manager: The validation manager instance
            retry_handler: Optional retry handler for transient errors
        """
        self.validation_manager = validation_manager
        self.retry_handler = retry_handler or MigrationRetryHandler(
            RetryPolicy(max_attempts=3, backoff_factor=2.0)
        )

    def validate_extraction(self, scope: ValidationScope):
        """
        Decorator for validating extraction operations.

        Args:
            scope: The validation scope for the operation
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get entity data before extraction if available
                entity_id = kwargs.get("entity_id")
                pre_validation_context = {"entity_id": entity_id} if entity_id else {}

                # Run pre-extraction validation
                self.validation_manager.run_validation(
                    ValidationPhase.PRE_EXTRACTION, scope, pre_validation_context
                )

                # Apply retry policy for extraction operations
                @self.retry_handler.with_retry(
                    retry_on_exceptions=[ConnectionError, TimeoutError, IOError],
                    phase="extraction",
                    scope=scope,
                )
                def _execute_with_retry():
                    return func(*args, **kwargs)

                try:
                    # Execute the extraction with retry support
                    result = _execute_with_retry()

                    # Run post-extraction validation if successful
                    validation_context = {"entity": result}
                    if entity_id:
                        validation_context["entity_id"] = entity_id

                    self.validation_manager.run_validation(
                        ValidationPhase.EXTRACTION, scope, validation_context
                    )
                    return result
                except Exception as e:
                    # Log validation error
                    self.validation_manager.add_issue(
                        ValidationIssue(
                            rule_id="extraction_error",
                            level=ValidationLevel.ERROR,
                            message=f"Extraction failed: {str(e)}",
                            entity_id=entity_id if entity_id else "unknown",
                            scope=scope,
                            phase=ValidationPhase.EXTRACTION,
                            context={"error": str(e), "exception_type": type(e).__name__},
                        )
                    )
                    raise

            return wrapper

        return decorator

    def validate_transformation(self, scope: ValidationScope):
        """
        Decorator for validating transformation operations.

        Args:
            scope: The validation scope for the operation
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get entity data before transformation
                source_entity = kwargs.get("source_entity")
                entity_id = (
                    getattr(source_entity, "id", None)
                    if source_entity
                    else kwargs.get("entity_id", "unknown")
                )

                pre_validation_context = {"source_entity": source_entity} if source_entity else {}
                if entity_id != "unknown":
                    pre_validation_context["entity_id"] = entity_id

                # Run pre-transformation validation
                self.validation_manager.run_validation(
                    ValidationPhase.PRE_TRANSFORMATION, scope, pre_validation_context
                )

                try:
                    # Execute the transformation
                    result = func(*args, **kwargs)

                    # Run post-transformation validation
                    validation_context = {
                        "source_entity": source_entity,
                        "target_entity": result,
                        "entity_id": entity_id,
                    }
                    self.validation_manager.run_validation(
                        ValidationPhase.TRANSFORMATION, scope, validation_context
                    )
                    return result
                except Exception as e:
                    # Log validation error
                    self.validation_manager.add_issue(
                        ValidationIssue(
                            rule_id="transformation_error",
                            level=ValidationLevel.ERROR,
                            message=f"Transformation failed: {str(e)}",
                            entity_id=entity_id,
                            scope=scope,
                            phase=ValidationPhase.TRANSFORMATION,
                            context={"error": str(e), "exception_type": type(e).__name__},
                        )
                    )
                    raise

            return wrapper

        return decorator

    def validate_loading(self, scope: ValidationScope):
        """
        Decorator for validating loading operations.

        Args:
            scope: The validation scope for the operation
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get entity data before loading
                entity = kwargs.get("entity")
                entity_id = (
                    getattr(entity, "id", None) if entity else kwargs.get("entity_id", "unknown")
                )

                pre_validation_context = {"entity": entity} if entity else {}
                if entity_id != "unknown":
                    pre_validation_context["entity_id"] = entity_id

                # Run pre-loading validation
                self.validation_manager.run_validation(
                    ValidationPhase.PRE_LOADING, scope, pre_validation_context
                )

                # Apply retry policy for loading operations (API calls)
                @self.retry_handler.with_retry(
                    retry_on_exceptions=[ConnectionError, TimeoutError, IOError],
                    phase="loading",
                    scope=scope,
                )
                def _execute_with_retry():
                    return func(*args, **kwargs)

                try:
                    # Execute the loading with retry support
                    result = _execute_with_retry()

                    # Run post-loading validation
                    validation_context = {
                        "entity": entity,
                        "api_result": result,
                        "entity_id": entity_id,
                    }
                    self.validation_manager.run_validation(
                        ValidationPhase.LOADING, scope, validation_context
                    )
                    return result
                except Exception as e:
                    # Log validation error
                    self.validation_manager.add_issue(
                        ValidationIssue(
                            rule_id="loading_error",
                            level=ValidationLevel.ERROR,
                            message=f"Loading failed: {str(e)}",
                            entity_id=entity_id,
                            scope=scope,
                            phase=ValidationPhase.LOADING,
                            context={"error": str(e), "exception_type": type(e).__name__},
                        )
                    )
                    raise

            return wrapper

        return decorator


class EnhancedMigration:
    """
    Enhanced migration wrapper that integrates the validation framework.

    This class wraps the ZephyrToQTestMigration class to add validation capabilities
    while maintaining the same interface.
    """

    def __init__(self, migration, database, project_key):
        """
        Initialize the enhanced migration wrapper.

        Args:
            migration: The ZephyrToQTestMigration instance to wrap
            database: Database manager instance
            project_key: The Zephyr project key
        """
        self.migration = migration
        self.db = database
        self.project_key = project_key

        # Initialize validation components
        self.validation_manager = ValidationManager(database, project_key)
        self.retry_handler = MigrationRetryHandler(RetryPolicy(max_retries=3, backoff_factor=2.0))

        # Initialize validator
        self.validator = MigrationValidator(self.validation_manager)

        # Initialize decorators
        self.decorators = MigrationValidationDecorators(self.validation_manager, self.retry_handler)

        # Register built-in rules
        for rule in get_built_in_rules():
            self.validation_manager.registry.register_rule(rule)

        # Set up method wrappers
        self._setup_method_wrappers()

    def _setup_method_wrappers(self):
        """Set up method wrappers for the migration class."""
        # Extract methods
        self.migration._extract_folders = self.decorators.validate_extraction(
            ValidationScope.FOLDER
        )(self.migration._extract_folders)

        self.migration._extract_test_cases = self.decorators.validate_extraction(
            ValidationScope.TEST_CASE
        )(self.migration._extract_test_cases)

        self.migration._extract_test_cycles = self.decorators.validate_extraction(
            ValidationScope.TEST_CYCLE
        )(self.migration._extract_test_cycles)

        self.migration._extract_test_executions = self.decorators.validate_extraction(
            ValidationScope.TEST_EXECUTION
        )(self.migration._extract_test_executions)

        # Transform methods
        self.migration._transform_project = self.decorators.validate_transformation(
            ValidationScope.PROJECT
        )(self.migration._transform_project)

        self.migration._transform_folders_to_modules = self.decorators.validate_transformation(
            ValidationScope.FOLDER
        )(self.migration._transform_folders_to_modules)

        self.migration._transform_test_cases = self.decorators.validate_transformation(
            ValidationScope.TEST_CASE
        )(self.migration._transform_test_cases)

        self.migration._transform_test_cycles = self.decorators.validate_transformation(
            ValidationScope.TEST_CYCLE
        )(self.migration._transform_test_cycles)

        self.migration._transform_test_executions = self.decorators.validate_transformation(
            ValidationScope.TEST_EXECUTION
        )(self.migration._transform_test_executions)

        # Load methods
        self.migration._create_module_in_qtest = self.decorators.validate_loading(
            ValidationScope.FOLDER
        )(self.migration._create_module_in_qtest)

        self.migration._create_test_case_in_qtest = self.decorators.validate_loading(
            ValidationScope.TEST_CASE
        )(self.migration._create_test_case_in_qtest)

        self.migration._create_test_cycle_in_qtest = self.decorators.validate_loading(
            ValidationScope.TEST_CYCLE
        )(self.migration._create_test_cycle_in_qtest)

        self.migration._create_execution_in_qtest = self.decorators.validate_loading(
            ValidationScope.TEST_EXECUTION
        )(self.migration._create_execution_in_qtest)

    def run_migration(self, phases=None):
        """
        Run the migration with validation.

        Args:
            phases: Optional list of phases to run
        """
        if not phases:
            phases = ["extract", "transform", "load"]

        # Run pre-migration validation
        self.validator.validate_pre_migration()

        # Run the migration
        result = self.migration.run_migration(phases)

        # Run post-migration validation
        self.validator.validate_post_migration()

        # Get validation report
        validation_report = self.validator.generate_validation_report()

        # Save validation report to database
        self.db.save_validation_report(self.project_key, validation_report)

        return result

    def extract_data(self):
        """Run extraction with validation."""
        # Run pre-extraction validation
        self.validator.validate_pre_phase(ValidationPhase.EXTRACTION)

        # Run extraction
        result = self.migration.extract_data()

        # Run post-extraction validation
        self.validator.validate_post_phase(ValidationPhase.EXTRACTION)

        return result

    def transform_data(self):
        """Run transformation with validation."""
        # Run pre-transformation validation
        self.validator.validate_pre_phase(ValidationPhase.TRANSFORMATION)

        # Run transformation
        result = self.migration.transform_data()

        # Run post-transformation validation
        self.validator.validate_post_phase(ValidationPhase.TRANSFORMATION)

        return result

    def load_data(self):
        """Run loading with validation."""
        # Run pre-loading validation
        self.validator.validate_pre_phase(ValidationPhase.LOADING)

        # Run loading
        result = self.migration.load_data()

        # Run post-loading validation
        self.validator.validate_post_phase(ValidationPhase.LOADING)

        return result

    def __getattr__(self, name):
        """Delegate attribute access to the underlying migration object."""
        return getattr(self.migration, name)


def get_enhanced_migration(migration, database, project_key):
    """
    Factory function to create enhanced migration instance.

    Args:
        migration: The ZephyrToQTestMigration instance
        database: Database manager instance
        project_key: The Zephyr project key

    Returns:
        EnhancedMigration: The enhanced migration wrapper
    """
    return EnhancedMigration(migration, database, project_key)
