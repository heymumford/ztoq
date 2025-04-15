"""
Model-specific factories for the ZTOQ testing framework.

This module provides factory classes for generating test instances
of the project's domain models.
"""

from datetime import datetime, timedelta
from typing import Any

# Import the base factory classes
from tests.fixtures.factories import BaseFactory, ModelFactory

# Import the models we need to create factories for
from ztoq.domain.models import OpenAPISpec
from ztoq.models import (
    Attachment,
    Case as TestCase,
    CaseStep,
    CustomField,
    CycleInfo as TestCycle,
    Environment,
    Execution as TestExecution,
    Folder,
    Link,
    Priority,
    Project,
    Status,
    ZephyrConfig,
)
from ztoq.qtest_models import QTestConfig, QTestProject, QTestTestCase, QTestTestCycle, QTestTestRun


class OpenAPISpecFactory(ModelFactory):
    """Factory for creating OpenAPISpec model instances for testing."""

    MODEL_CLASS = OpenAPISpec

    DEFAULTS = {
        "title": lambda: f"API Spec {BaseFactory.random_string(5)}",
        "version": lambda: f"1.{BaseFactory.random_int(0, 10)}.{BaseFactory.random_int(0, 99)}",
        "data": lambda: {
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/test": {"get": {"summary": "Test endpoint"}}},
            "components": {"schemas": {}},
        },
        "path": lambda: f"/path/to/api-spec-{BaseFactory.random_string(5)}.yaml",
    }


class ProjectFactory(ModelFactory):
    """Factory for creating Project model instances for testing."""

    MODEL_CLASS = Project

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "key": lambda: BaseFactory.random_string(4).upper(),
        "name": lambda: f"Project-{BaseFactory.random_string(8)}",
        "description": lambda: f"Test project description {BaseFactory.random_string(15)}",
    }


class PriorityFactory(ModelFactory):
    """Factory for creating Priority model instances for testing."""

    MODEL_CLASS = Priority

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: BaseFactory.random_choice(["High", "Medium", "Low"]),
        "description": lambda: f"Priority description {BaseFactory.random_string(10)}",
        "color": lambda: BaseFactory.random_choice(["#ff0000", "#00ff00", "#0000ff"]),
        "rank": lambda: BaseFactory.random_int(1, 5),
    }


class StatusFactory(ModelFactory):
    """Factory for creating Status model instances for testing."""

    MODEL_CLASS = Status

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: BaseFactory.random_choice(["Active", "Draft", "Completed", "Deprecated"]),
        "description": lambda: f"Status description {BaseFactory.random_string(10)}",
        "color": lambda: BaseFactory.random_choice(["#ffff00", "#00ffff", "#ff00ff"]),
        "type": lambda: BaseFactory.random_choice(["TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION"]),
    }


class CaseStepFactory(ModelFactory):
    """Factory for creating CaseStep model instances for testing."""

    MODEL_CLASS = CaseStep

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "index": lambda: BaseFactory.random_int(1, 10),
        "description": lambda: f"Step description {BaseFactory.random_string(20)}",
        "expected_result": lambda: f"Expected result {BaseFactory.random_string(20)}",
        "data": lambda: None,
        "actual_result": lambda: None,
        "status": lambda: None,
        "attachments": list,
    }


class CustomFieldFactory(ModelFactory):
    """Factory for creating CustomField model instances for testing."""

    MODEL_CLASS = CustomField

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: f"CustomField-{BaseFactory.random_string(5)}",
        "type": lambda: BaseFactory.random_choice(["text", "paragraph", "checkbox", "dropdown"]),
        "value": lambda: BaseFactory.random_string(10),
    }

    @classmethod
    def create(cls, **kwargs: Any) -> CustomField:
        """
        Create a CustomField with type-appropriate value.

        This overrides the default create method to ensure that
        the value is appropriate for the specified field type.

        Args:
            **kwargs: Fields to override default values

        Returns:
            CustomField: Created model instance
        """
        # Get the field type if provided
        field_type = kwargs.get("type")

        # If field type is provided but value is not, generate appropriate value
        if field_type and "value" not in kwargs:
            if field_type == "checkbox":
                kwargs["value"] = BaseFactory.random_bool()
            elif field_type == "numeric":
                kwargs["value"] = BaseFactory.random_int(1, 100)
            elif field_type in ["dropdown", "radio"]:
                kwargs["value"] = BaseFactory.random_choice(["Option 1", "Option 2", "Option 3"])
            elif field_type == "multipleSelect":
                kwargs["value"] = BaseFactory.random_subset(
                    ["Option 1", "Option 2", "Option 3", "Option 4"], min_size=1, max_size=3,
                )

        # Create the custom field using the parent class method
        return super().create(**kwargs)


class LinkFactory(ModelFactory):
    """Factory for creating Link model instances for testing."""

    MODEL_CLASS = Link

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: f"Link-{BaseFactory.random_string(5)}",
        "url": lambda: f"https://example.com/{BaseFactory.random_string(10)}",
        "description": lambda: f"Link description {BaseFactory.random_string(15)}",
        "type": lambda: BaseFactory.random_choice(["issue", "web", "testCycle"]),
    }


class AttachmentFactory(ModelFactory):
    """Factory for creating Attachment model instances for testing."""

    MODEL_CLASS = Attachment

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "filename": lambda: f"attachment-{BaseFactory.random_string(5)}.txt",
        "content_type": lambda: "text/plain",
        "size": lambda: BaseFactory.random_int(100, 10000),
        "created_on": lambda: BaseFactory.random_date(),
        "created_by": lambda: f"user-{BaseFactory.random_string(5)}",
        "content": lambda: None,
    }


class FolderFactory(ModelFactory):
    """Factory for creating Folder model instances for testing."""

    MODEL_CLASS = Folder

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: f"Folder-{BaseFactory.random_string(5)}",
        "folder_type": lambda: BaseFactory.random_choice(["TEST_CASE", "TEST_CYCLE"]),
        "parent_id": lambda: None,
        "project_key": lambda: BaseFactory.random_string(4).upper(),
    }


class EnvironmentFactory(ModelFactory):
    """Factory for creating Environment model instances for testing."""

    MODEL_CLASS = Environment

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "name": lambda: f"Environment-{BaseFactory.random_string(5)}",
        "description": lambda: f"Environment description {BaseFactory.random_string(15)}",
    }


class ZephyrConfigFactory(ModelFactory):
    """Factory for creating ZephyrConfig model instances for testing."""

    MODEL_CLASS = ZephyrConfig

    DEFAULTS = {
        "base_url": lambda: "https://api.example.com/v2",
        "api_token": lambda: f"token-{BaseFactory.random_string(20)}",
        "project_key": lambda: BaseFactory.random_string(4).upper(),
    }


class TestCaseFactory(ModelFactory):
    """Factory for creating TestCase model instances for testing."""

    MODEL_CLASS = TestCase

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "key": lambda: f"TC-{BaseFactory.random_int(100, 999)}",
        "name": lambda: f"Test Case {BaseFactory.random_string(8)}",
        "objective": lambda: f"Test objective {BaseFactory.random_string(20)}",
        "precondition": lambda: f"Test precondition {BaseFactory.random_string(20)}",
        "description": lambda: f"Test case description {BaseFactory.random_string(15)}",
        "status": lambda: BaseFactory.random_choice(["Active", "Draft", "Deprecated"]),
        "priority": lambda: PriorityFactory.create(),
        "priority_name": lambda: BaseFactory.random_choice(["High", "Medium", "Low"]),
        "folder": lambda: str(BaseFactory.random_int(1000, 9999)),
        "folder_name": lambda: f"Folder-{BaseFactory.random_string(5)}",
        "owner": lambda: str(BaseFactory.random_int(1000, 9999)),
        "owner_name": lambda: f"User-{BaseFactory.random_string(5)}",
        "created_on": lambda: BaseFactory.random_date(),
        "created_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "updated_on": lambda: BaseFactory.random_date(),
        "updated_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "version": lambda: f"1.{BaseFactory.random_int(0, 9)}",
        "estimated_time": lambda: BaseFactory.random_int(60, 3600),
        "labels": list,
        "steps": list,
        "custom_fields": list,
        "links": list,
        "scripts": list,
        "versions": list,
        "attachments": list,
    }

    @classmethod
    def create_with_steps(cls, step_count: int = 3, **kwargs: Any) -> TestCase:
        """
        Create a TestCase with the specified number of steps.

        Args:
            step_count: Number of steps to create
            **kwargs: Additional fields to override

        Returns:
            TestCase: Created model instance with steps
        """
        # Create the steps
        steps = []
        for i in range(step_count):
            steps.append(CaseStepFactory.create(index=i + 1))

        # Add steps to kwargs
        if "steps" not in kwargs:
            kwargs["steps"] = steps

        # Create the test case
        return cls.create(**kwargs)


class TestCycleFactory(ModelFactory):
    """Factory for creating TestCycle model instances for testing."""

    MODEL_CLASS = TestCycle

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "key": lambda: f"CY-{BaseFactory.random_int(100, 999)}",
        "name": lambda: f"Test Cycle {BaseFactory.random_string(8)}",
        "description": lambda: f"Test cycle description {BaseFactory.random_string(15)}",
        "status": lambda: BaseFactory.random_choice(["Active", "Draft", "Completed"]),
        "status_name": lambda: BaseFactory.random_choice(["Active", "Draft", "Completed"]),
        "folder": lambda: str(BaseFactory.random_int(1000, 9999)),
        "folder_name": lambda: f"Folder-{BaseFactory.random_string(5)}",
        "project_key": lambda: BaseFactory.random_string(4).upper(),
        "owner": lambda: str(BaseFactory.random_int(1000, 9999)),
        "owner_name": lambda: f"User-{BaseFactory.random_string(5)}",
        "created_on": lambda: BaseFactory.random_date(),
        "created_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "updated_on": lambda: BaseFactory.random_date(),
        "updated_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "custom_fields": list,
        "links": list,
        "attachments": list,
    }


class TestExecutionFactory(ModelFactory):
    """Factory for creating TestExecution model instances for testing."""

    MODEL_CLASS = TestExecution

    DEFAULTS = {
        "id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "test_case_key": lambda: f"TC-{BaseFactory.random_int(100, 999)}",
        "cycle_id": lambda: str(BaseFactory.random_int(1000, 9999)),
        "cycle_name": lambda: f"Cycle-{BaseFactory.random_string(5)}",
        "status": lambda: BaseFactory.random_choice(["Passed", "Failed", "Blocked", "Not Run"]),
        "status_name": lambda: BaseFactory.random_choice(
            ["Passed", "Failed", "Blocked", "Not Run"],
        ),
        "environment": lambda: str(BaseFactory.random_int(1000, 9999)),
        "environment_name": lambda: f"Environment-{BaseFactory.random_string(5)}",
        "executed_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "executed_by_name": lambda: f"User-{BaseFactory.random_string(5)}",
        "executed_on": lambda: BaseFactory.random_date(),
        "created_on": lambda: BaseFactory.random_date(),
        "created_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "updated_on": lambda: BaseFactory.random_date(),
        "updated_by": lambda: str(BaseFactory.random_int(1000, 9999)),
        "actual_time": lambda: BaseFactory.random_int(60, 3600),
        "comment": lambda: f"Execution comment {BaseFactory.random_string(20)}",
        "steps": list,
        "custom_fields": list,
        "links": list,
        "attachments": list,
    }

    @classmethod
    def create_with_steps(cls, test_case: TestCase, **kwargs: Any) -> TestExecution:
        """
        Create a TestExecution with steps based on a TestCase.

        Args:
            test_case: The test case to base the execution on
            **kwargs: Additional fields to override

        Returns:
            TestExecution: Created model instance with steps
        """
        # Copy the steps from the test case and add status and actual result
        steps = []
        for case_step in test_case.steps:
            # Create an execution step based on the test case step
            execution_step = CaseStepFactory.create(
                id=case_step.id,
                index=case_step.index,
                description=case_step.description,
                expected_result=case_step.expected_result,
                data=case_step.data,
                status=BaseFactory.random_choice(["Passed", "Failed", "Blocked", "Not Run"]),
                actual_result=f"Actual result {BaseFactory.random_string(15)}",
            )
            steps.append(execution_step)

        # Add steps to kwargs
        if "steps" not in kwargs:
            kwargs["steps"] = steps

        # Add test case key if not provided
        if "test_case_key" not in kwargs:
            kwargs["test_case_key"] = test_case.key

        # Create the test execution
        return cls.create(**kwargs)


class QTestConfigFactory(ModelFactory):
    """Factory for creating QTestConfig model instances for testing."""

    MODEL_CLASS = QTestConfig

    DEFAULTS = {
        "base_url": lambda: "https://qtest.example.com",
        "username": lambda: f"user_{BaseFactory.random_string(5)}",
        "password": lambda: f"pass_{BaseFactory.random_string(10)}",
        "project_id": lambda: BaseFactory.random_int(1000, 9999),
    }


class QTestProjectFactory(ModelFactory):
    """Factory for creating QTestProject model instances for testing."""

    MODEL_CLASS = QTestProject

    DEFAULTS = {
        "id": lambda: BaseFactory.random_int(1000, 9999),
        "name": lambda: f"qTest Project {BaseFactory.random_string(8)}",
        "description": lambda: f"qTest project description {BaseFactory.random_string(15)}",
        "status_name": lambda: "Active",
    }

    @classmethod
    def create(cls, **kwargs: Any) -> QTestProject:
        """
        Create a QTestProject with valid dates.

        This overrides the default create method to ensure that
        the end_date is always after the start_date.

        Args:
            **kwargs: Fields to override default values

        Returns:
            QTestProject: Created model instance
        """
        # Generate a valid start date (default 1 year ago)
        if "start_date" not in kwargs:
            start_date = datetime.now() - timedelta(days=180)
            kwargs["start_date"] = start_date
        else:
            start_date = kwargs["start_date"]

        # Generate a valid end date (after the start date)
        if "end_date" not in kwargs:
            # Set end date to start date + 90 days
            kwargs["end_date"] = start_date + timedelta(days=90)
        elif kwargs["end_date"] <= start_date:
            # If end date is provided but invalid, fix it
            kwargs["end_date"] = start_date + timedelta(days=90)

        # Create the project using the parent class method
        return super().create(**kwargs)


class QTestTestCaseFactory(ModelFactory):
    """Factory for creating QTestTestCase model instances for testing."""

    MODEL_CLASS = QTestTestCase

    DEFAULTS = {
        "id": lambda: BaseFactory.random_int(1000, 9999),
        "pid": lambda: f"TC-{BaseFactory.random_int(100, 999)}",
        "name": lambda: f"qTest Test Case {BaseFactory.random_string(8)}",
        "description": lambda: f"qTest test case description {BaseFactory.random_string(15)}",
        "project_id": lambda: BaseFactory.random_int(1000, 9999),
        "module_id": lambda: BaseFactory.random_int(1000, 9999),
        "test_steps": list,
        "properties": list,
        "priority_id": lambda: BaseFactory.random_int(1, 5),
        "creator_id": lambda: BaseFactory.random_int(1000, 9999),
        "attachments": list,
        "create_date": lambda: BaseFactory.random_date(),
        "last_modified_date": lambda: BaseFactory.random_date(),
        "shared": lambda: False,
        "test_case_version_id": lambda: 1,
        "version": lambda: 1,
    }


class QTestTestCycleFactory(ModelFactory):
    """Factory for creating QTestTestCycle model instances for testing."""

    MODEL_CLASS = QTestTestCycle

    DEFAULTS = {
        "id": lambda: BaseFactory.random_int(1000, 9999),
        "name": lambda: f"qTest Test Cycle {BaseFactory.random_string(8)}",
        "description": lambda: f"qTest test cycle description {BaseFactory.random_string(15)}",
        "pid": lambda: f"CY-{BaseFactory.random_int(100, 999)}",
        "project_id": lambda: BaseFactory.random_int(1000, 9999),
        "release_id": lambda: BaseFactory.random_int(1000, 9999),
        "properties": list,
    }

    @classmethod
    def create(cls, **kwargs: Any) -> QTestTestCycle:
        """
        Create a QTestTestCycle with valid dates.

        This overrides the default create method to ensure that
        the end_date is always after the start_date.

        Args:
            **kwargs: Fields to override default values

        Returns:
            QTestTestCycle: Created model instance
        """
        # Generate a valid start date
        if "start_date" not in kwargs:
            start_date = datetime.now() - timedelta(days=30)
            kwargs["start_date"] = start_date
        else:
            start_date = kwargs["start_date"]

        # Generate a valid end date (after the start date)
        if "end_date" not in kwargs:
            # Set end date to start date + 14 days
            kwargs["end_date"] = start_date + timedelta(days=14)
        elif kwargs["end_date"] <= start_date:
            # If end date is provided but invalid, fix it
            kwargs["end_date"] = start_date + timedelta(days=14)

        # Create the test cycle using the parent class method
        return super().create(**kwargs)


class QTestTestRunFactory(ModelFactory):
    """Factory for creating QTestTestRun model instances for testing."""

    MODEL_CLASS = QTestTestRun

    DEFAULTS = {
        "id": lambda: BaseFactory.random_int(1000, 9999),
        "name": lambda: f"qTest Test Run {BaseFactory.random_string(8)}",
        "description": lambda: f"qTest test run description {BaseFactory.random_string(15)}",
        "pid": lambda: f"TR-{BaseFactory.random_int(100, 999)}",
        "test_case_id": lambda: BaseFactory.random_int(1000, 9999),
        "test_cycle_id": lambda: BaseFactory.random_int(1000, 9999),
        "project_id": lambda: BaseFactory.random_int(1000, 9999),
        "properties": list,
        "status": lambda: BaseFactory.random_choice(["Not Run", "Passed", "Failed", "Blocked"]),
        "created_date": lambda: BaseFactory.random_date(),
    }
