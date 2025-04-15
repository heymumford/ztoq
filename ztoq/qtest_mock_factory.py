"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Mock factory for generating qTest entity objects.

This module provides factories for generating mock qTest entities for testing.
Each factory can generate individual entities or collections of entities.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from pydantic import BaseModel
from ztoq.qtest_models import (
    QTestAutomationSettings,
    QTestConfig,
    QTestCustomField,
    QTestDataset,
    QTestDatasetRow,
    QTestField,
    QTestLink,
    QTestModule,
    QTestPaginatedResponse,
    QTestParameter,
    QTestParameterValue,
    QTestProject,
    QTestPulseAction,
    QTestPulseActionParameter,
    QTestPulseCondition,
    QTestPulseConstant,
    QTestPulseRule,
    QTestPulseTrigger,
    QTestRelease,
    QTestScenarioFeature,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
    QTestTestExecution,
    QTestTestLog,
    QTestTestRun,
)


class MockFactory:
    """Base class for all mock factories with common utility methods."""

    @staticmethod
    def random_id() -> int:
        """Generate a random ID."""
        return random.randint(1000, 9999)

    @staticmethod
    def random_string(prefix: str = "") -> str:
        """Generate a random string with optional prefix."""
        return f"{prefix}{uuid.uuid4().hex[:8]}"

    @staticmethod
    def random_date(days_ago: int = 30) -> datetime:
        """Generate a random date within the last N days."""
        return datetime.now() - timedelta(days=random.randint(0, days_ago))

    @staticmethod
    def random_bool() -> bool:
        """Generate a random boolean value."""
        return random.choice([True, False])

    @staticmethod
    def random_enum(enum_class: Any) -> Any:
        """Generate a random value from an Enum class."""
        return random.choice(list(enum_class))

    @staticmethod
    def random_list_item(items: List[Any]) -> Any:
        """Choose a random item from a list."""
        return random.choice(items)

    @staticmethod
    def dict_to_model(model_class: Any, data: Dict[str, Any]) -> BaseModel:
        """Convert a dictionary to a Pydantic model instance."""
        return model_class(**data)


class QTestProjectFactory(MockFactory):
    """Factory for qTest Project entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestProject:
        """Create a single qTest Project."""
        start_date = kwargs.get("start_date", cls.random_date(365))
        project_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Project-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Project')}"
            ),
            "start_date": start_date,
            "end_date": kwargs.get("end_date", start_date + timedelta(days=180)),
            "status_name": kwargs.get("status_name", "Active"),
        }
        return QTestProject(**project_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[QTestProject]:
        """Create multiple qTest Projects."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestModuleFactory(MockFactory):
    """Factory for qTest Module entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestModule:
        """Create a single qTest Module."""
        module_id = kwargs.get("id", cls.random_id())
        module_data = {
            "id": module_id,
            "name": kwargs.get("name", cls.random_string("Module-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Module')}"
            ),
            "parent_id": kwargs.get("parent_id"),
            "pid": kwargs.get("pid", f"MD-{module_id}"),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "path": kwargs.get("path"),
        }

        # Build path if not provided
        if not module_data["path"]:
            if module_data["parent_id"]:
                parent_name = kwargs.get("parent_name", "Parent Module")
                module_data["path"] = f"{parent_name}/{module_data['name']}"
            else:
                module_data["path"] = module_data["name"]

        return QTestModule(**module_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[QTestModule]:
        """Create multiple qTest Modules."""
        modules = []
        parent_id = kwargs.get("parent_id")

        # Create root module if needed
        if not parent_id and kwargs.get("create_hierarchy", False):
            root = cls.create(name="Root Module")
            modules.append(root)
            parent_id = root.id

        # Create child modules
        for i in range(count):
            module = cls.create(
                parent_id=parent_id,
                parent_name=parent_id and "Root Module" or None,
                name=f"Module-{i+1}",
                **kwargs,
            )
            modules.append(module)

        return modules


class QTestCustomFieldFactory(MockFactory):
    """Factory for qTest CustomField entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestCustomField:
        """Create a single qTest Custom Field."""
        field_type = kwargs.get(
            "field_type", cls.random_list_item(QTestCustomField.SUPPORTED_TYPES)
        )
        field_id = kwargs.get("field_id", cls.random_id())

        # Generate appropriate value based on type
        if "field_value" in kwargs:
            field_value = kwargs["field_value"]
        else:
            if field_type == "STRING":
                field_value = cls.random_string("Value-")
            elif field_type == "NUMBER":
                field_value = random.randint(1, 100)
            elif field_type == "DATE":
                field_value = cls.random_date(90).isoformat()
            elif field_type == "CHECKBOX":
                field_value = cls.random_bool()
            elif field_type == "USER":
                field_value = {"id": cls.random_id(), "name": cls.random_string("User-")}
            elif field_type == "MULTI_USER":
                field_value = [
                    {"id": cls.random_id(), "name": cls.random_string("User-")} for _ in range(2)
                ]
            elif field_type == "MULTI_VALUE":
                field_value = [cls.random_string("Option-") for _ in range(2)]
            elif field_type == "RICH_TEXT":
                field_value = f"<p>{cls.random_string('Rich text value-')}</p>"
            else:
                field_value = cls.random_string("Value-")

        field_data = {
            "field_id": field_id,
            "field_name": kwargs.get("field_name", cls.random_string("Field-")),
            "field_type": field_type,
            "field_value": field_value,
            "is_required": kwargs.get("is_required", False),
        }

        return QTestCustomField(**field_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestCustomField]:
        """Create multiple qTest Custom Fields."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestStepFactory(MockFactory):
    """Factory for qTest Test Step entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestStep:
        """Create a single qTest Test Step."""
        step_data = {
            "id": kwargs.get("id", cls.random_id()),
            "description": kwargs.get(
                "description", f"Step {kwargs.get('order', 1)}: {cls.random_string()}"
            ),
            "expected_result": kwargs.get(
                "expected_result", f"Expected result for step {kwargs.get('order', 1)}"
            ),
            "order": kwargs.get("order", 1),
            "attachments": kwargs.get("attachments", []),
        }

        return QTestStep(**step_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestStep]:
        """Create multiple qTest Test Steps with sequential order numbers."""
        return [cls.create(order=i + 1, **kwargs) for i in range(count)]


class QTestTestCaseFactory(MockFactory):
    """Factory for qTest Test Case entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestTestCase:
        """Create a single qTest Test Case."""
        test_case_id = kwargs.get("id", cls.random_id())
        create_date = kwargs.get("create_date", cls.random_date(90))
        module_id = kwargs.get("module_id", cls.random_id())

        # Create test steps with sequential order
        if "test_steps" not in kwargs:
            step_count = kwargs.get("step_count", 3)
            test_steps = []
            for i in range(step_count):
                test_steps.append(QTestStepFactory.create(order=i + 1))
        else:
            test_steps = kwargs["test_steps"]

        # Create automation settings if not provided
        if "automation" not in kwargs and cls.random_bool():
            automation = QTestAutomationSettingsFactory.create()
        else:
            automation = kwargs.get("automation")

        test_case_data = {
            "id": test_case_id,
            "pid": kwargs.get("pid", f"TC-{test_case_id}"),
            "name": kwargs.get("name", cls.random_string("Test Case-")),
            "description": kwargs.get(
                "description", f"Description for test case {kwargs.get('name', 'Test Case')}"
            ),
            "precondition": kwargs.get("precondition", "Test case precondition"),
            "test_steps": test_steps,
            "properties": kwargs.get("properties", []),
            "parent_id": kwargs.get("parent_id"),
            "module_id": module_id,
            "priority_id": kwargs.get("priority_id", random.randint(1, 5)),
            "creator_id": kwargs.get("creator_id", cls.random_id()),
            "attachments": kwargs.get("attachments", []),
            "create_date": create_date,
            "last_modified_date": kwargs.get("last_modified_date", create_date),
            "automation": automation,
            "shared": kwargs.get("shared", False),
            "test_case_version_id": kwargs.get("test_case_version_id", 1),
            "version": kwargs.get("version", 1),
            "project_id": kwargs.get("project_id", cls.random_id()),
        }

        return QTestTestCase(**test_case_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[QTestTestCase]:
        """Create multiple qTest Test Cases."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestReleaseFactory(MockFactory):
    """Factory for qTest Release entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestRelease:
        """Create a single qTest Release."""
        release_id = kwargs.get("id", cls.random_id())
        start_date = kwargs.get("start_date", cls.random_date(90))

        release_data = {
            "id": release_id,
            "name": kwargs.get("name", cls.random_string("Release-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Release')}"
            ),
            "pid": kwargs.get("pid", f"RL-{release_id}"),
            "start_date": start_date,
            "end_date": kwargs.get("end_date", start_date + timedelta(days=90)),
            "project_id": kwargs.get("project_id", cls.random_id()),
        }

        return QTestRelease(**release_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestRelease]:
        """Create multiple qTest Releases."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestTestCycleFactory(MockFactory):
    """Factory for qTest Test Cycle entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestTestCycle:
        """Create a single qTest Test Cycle."""
        cycle_id = kwargs.get("id", cls.random_id())
        start_date = kwargs.get("start_date", cls.random_date(30))

        cycle_data = {
            "id": cycle_id,
            "name": kwargs.get("name", cls.random_string("Test Cycle-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Test Cycle')}"
            ),
            "parent_id": kwargs.get("parent_id"),
            "pid": kwargs.get("pid", f"CY-{cycle_id}"),
            "release_id": kwargs.get("release_id", cls.random_id()),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "properties": kwargs.get("properties", QTestCustomFieldFactory.create_batch(2)),
            "start_date": start_date,
            "end_date": kwargs.get("end_date", start_date + timedelta(days=14)),
        }

        return QTestTestCycle(**cycle_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestTestCycle]:
        """Create multiple qTest Test Cycles."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestTestRunFactory(MockFactory):
    """Factory for qTest Test Run entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestTestRun:
        """Create a single qTest Test Run."""
        run_id = kwargs.get("id", cls.random_id())
        test_case = kwargs.get("test_case", None)
        if test_case:
            test_case_id = test_case.id
            run_name = f"Run for {test_case.name}"
        else:
            test_case_id = kwargs.get("test_case_id", cls.random_id())
            run_name = cls.random_string("Test Run-")

        test_cycle_id = kwargs.get("test_cycle_id", cls.random_id())
        created_date = kwargs.get("created_date", cls.random_date())

        run_data = {
            "id": run_id,
            "name": kwargs.get("name", run_name),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', run_name)}"
            ),
            "pid": kwargs.get("pid", f"TR-{run_id}"),
            "test_case_version_id": kwargs.get("test_case_version_id", 1),
            "test_case_id": test_case_id,
            "test_cycle_id": test_cycle_id,
            "project_id": kwargs.get("project_id", cls.random_id()),
            "properties": kwargs.get("properties", []),
            "status": kwargs.get("status", "Not Run"),
            "assigned_to": kwargs.get(
                "assigned_to", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "created_date": created_date,
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "planned_execution_date": kwargs.get(
                "planned_execution_date", created_date + timedelta(days=1)
            ),
            "actual_execution_date": kwargs.get("actual_execution_date"),
            "latest_test_log_id": kwargs.get("latest_test_log_id"),
        }

        return QTestTestRun(**run_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestTestRun]:
        """Create multiple qTest Test Runs."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestTestLogFactory(MockFactory):
    """Factory for qTest Test Log entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestTestLog:
        """Create a single qTest Test Log."""
        status = kwargs.get("status", cls.random_list_item(QTestTestLog.VALID_STATUSES))
        execution_date = kwargs.get("execution_date", cls.random_date(10))

        # Test run ID is required for new test logs
        test_run_id = kwargs.get("test_run_id", cls.random_id())

        log_data = {
            "id": kwargs.get("id", cls.random_id()),
            "status": status,
            "execution_date": execution_date,
            "note": kwargs.get("note", f"Test executed with result: {status}"),
            "attachments": kwargs.get("attachments", []),
            "properties": kwargs.get("properties", []),
            "test_run_id": test_run_id,
            "executed_by": kwargs.get(
                "executed_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "defects": kwargs.get("defects", []),
            "test_step_logs": kwargs.get("test_step_logs"),
            "actual_results": kwargs.get(
                "actual_results", f"Actual results for test with status: {status}"
            ),
        }

        return QTestTestLog(**log_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestTestLog]:
        """Create multiple qTest Test Logs."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestAttachmentFactory(MockFactory):
    """Factory for qTest Attachment entities."""

    CONTENT_TYPES = [
        "image/png",
        "image/jpeg",
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/json",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a single qTest Attachment dictionary (not model)."""
        content_type = kwargs.get("content_type", cls.random_list_item(cls.CONTENT_TYPES))

        attachment_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", f"{cls.random_string()}.{content_type.split('/')[-1]}"),
            "contentType": kwargs.get("contentType", content_type),
            "size": kwargs.get("size", random.randint(1024, 1048576)),  # 1KB to 1MB
            "createdDate": kwargs.get("createdDate", cls.random_date().isoformat()),
            "webUrl": kwargs.get(
                "webUrl", f"https://example.com/attachments/{kwargs.get('id', cls.random_id())}"
            ),
        }

        # Add binary data if specified
        if "data" in kwargs:
            attachment_data["data"] = kwargs["data"]

        return attachment_data

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple qTest Attachments."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestParameterValueFactory(MockFactory):
    """Factory for qTest Parameter Value entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestParameterValue:
        """Create a single qTest Parameter Value."""
        value_id = kwargs.get("id", cls.random_id())
        parameter_id = kwargs.get("parameter_id", cls.random_id())

        value_data = {
            "id": value_id,
            "value": kwargs.get("value", f"Value-{cls.random_string()}"),
            "parameter_id": parameter_id,
        }

        return QTestParameterValue(**value_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestParameterValue]:
        """Create multiple qTest Parameter Values."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestParameterFactory(MockFactory):
    """Factory for qTest Parameter entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestParameter:
        """Create a single qTest Parameter."""
        param_id = kwargs.get("id", cls.random_id())
        project_id = kwargs.get("project_id", cls.random_id())

        # Create parameter values separately if not provided
        if "values" not in kwargs:
            # Create values using QTestParameterValueFactory
            values = []
            for i in range(random.randint(2, 5)):
                value = QTestParameterValueFactory.create(
                    parameter_id=param_id, value=f"Value-{i+1}"
                )
                values.append(value)
        else:
            values = kwargs["values"]

        param_data = {
            "id": param_id,
            "name": kwargs.get("name", cls.random_string("Parameter-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Parameter')}"
            ),
            "project_id": project_id,
            "status": kwargs.get("status", "Active"),
            "values": values,
        }

        return QTestParameter(**param_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestParameter]:
        """Create multiple qTest Parameters."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestDatasetFactory(MockFactory):
    """Factory for qTest Dataset entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestDataset:
        """Create a single qTest Dataset."""
        dataset_id = kwargs.get("id", cls.random_id())

        # Default parameter names
        parameter_names = kwargs.get("parameter_names", ["param1", "param2", "param3"])

        # Create rows if not provided
        if "rows" not in kwargs:
            # Generate 2-5 rows of data
            rows = []
            for i in range(random.randint(2, 5)):
                row_values = {param: f"Value-{i+1}-{param}" for param in parameter_names}
                rows.append(
                    QTestDatasetRow(
                        id=cls.random_id(),
                        dataset_id=dataset_id,
                        values=row_values,
                        name=f"Row {i+1}",
                        description=f"Description for row {i+1}",
                    )
                )
        else:
            rows = kwargs["rows"]

        dataset_data = {
            "id": dataset_id,
            "name": kwargs.get("name", cls.random_string("Dataset-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Dataset')}"
            ),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "status": kwargs.get("status", "Active"),
            "rows": rows,
            "parameter_names": parameter_names,
            "created_date": kwargs.get("created_date", cls.random_date()),
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
        }

        return QTestDataset(**dataset_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestDataset]:
        """Create multiple qTest Datasets."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseTriggerFactory(MockFactory):
    """Factory for qTest Pulse Trigger entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseTrigger:
        """Create a single qTest Pulse Trigger."""
        from ztoq.qtest_models import QTestPulseEventType

        event_type = kwargs.get("event_type", cls.random_list_item(list(QTestPulseEventType)))

        # Create conditions if not provided
        if "conditions" not in kwargs:
            # Generate 0-3 conditions using the condition factory
            conditions = []
            for _ in range(random.randint(1, 3)):
                condition = QTestPulseConditionFactory.create()
                conditions.append(condition)
        else:
            conditions = kwargs["conditions"]

        trigger_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Trigger-")),
            "event_type": event_type,
            "project_id": kwargs.get("project_id", cls.random_id()),
            "conditions": conditions,
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "created_date": kwargs.get("created_date", cls.random_date().isoformat()),
        }

        return QTestPulseTrigger(**trigger_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseTrigger]:
        """Create multiple qTest Pulse Triggers."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseActionFactory(MockFactory):
    """Factory for qTest Pulse Action entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseAction:
        """Create a single qTest Pulse Action."""
        from ztoq.qtest_models import QTestPulseActionType

        # If action_type is provided as string, convert to enum
        if "action_type" in kwargs and isinstance(kwargs["action_type"], str):
            kwargs["action_type"] = QTestPulseActionType(kwargs["action_type"])

        # Use SEND_MAIL as default action type for reliable parameter structure
        action_type = kwargs.get("action_type", QTestPulseActionType.SEND_MAIL)

        # Create parameters if not provided
        if "parameters" not in kwargs:
            # Generate parameters based on action type
            parameters = []
            if action_type == QTestPulseActionType.CREATE_DEFECT:
                parameters = [
                    QTestPulseActionParameterFactory.create(name="issueType", value="Bug"),
                    QTestPulseActionParameterFactory.create(
                        name="summary", value="{{testCase.name}} failed"
                    ),
                    QTestPulseActionParameterFactory.create(
                        name="description", value="Failure in {{testCase.name}}"
                    ),
                ]
            elif action_type == QTestPulseActionType.SEND_MAIL:
                parameters = [
                    QTestPulseActionParameterFactory.create(
                        name="recipients", value="test@example.com"
                    ),
                    QTestPulseActionParameterFactory.create(
                        name="subject", value="Test Notification: {{testCase.name}}"
                    ),
                    QTestPulseActionParameterFactory.create(
                        name="body", value="Test case {{testCase.name}} has been updated."
                    ),
                ]
            elif action_type == QTestPulseActionType.UPDATE_FIELD_VALUE:
                parameters = [
                    QTestPulseActionParameterFactory.create(name="field_id", value=cls.random_id()),
                    QTestPulseActionParameterFactory.create(name="field_value", value="New Value"),
                ]
            elif action_type == QTestPulseActionType.WEBHOOK:
                parameters = [
                    QTestPulseActionParameterFactory.create(
                        name="url", value="https://example.com/webhook"
                    ),
                    QTestPulseActionParameterFactory.create(name="method", value="POST"),
                ]
            elif action_type == QTestPulseActionType.SLACK:
                parameters = [
                    QTestPulseActionParameterFactory.create(
                        name="webhook_url", value="https://slack.com/api/webhook"
                    ),
                    QTestPulseActionParameterFactory.create(
                        name="message", value="Test notification from qTest"
                    ),
                ]
            elif action_type == QTestPulseActionType.UPDATE_TEST_RUN_STATUS:
                parameters = [
                    QTestPulseActionParameterFactory.create(name="status", value="Passed")
                ]
            else:
                # Generate generic parameters with at least required fields
                parameters = [
                    QTestPulseActionParameterFactory.create(name="param1", value="value1"),
                    QTestPulseActionParameterFactory.create(name="param2", value="value2"),
                ]
        else:
            parameters = kwargs["parameters"]

        action_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Action-")),
            "action_type": action_type,
            "project_id": kwargs.get("project_id", cls.random_id()),
            "parameters": parameters,
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "created_date": kwargs.get("created_date", cls.random_date().isoformat()),
        }

        return QTestPulseAction(**action_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseAction]:
        """Create multiple qTest Pulse Actions with same configuration."""
        # Create a test object first to ensure validation passes
        action = cls.create(**kwargs)
        # Then create batch with the same configuration
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseConstantFactory(MockFactory):
    """Factory for qTest Pulse Constant entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseConstant:
        """Create a single qTest Pulse Constant."""
        constant_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("CONSTANT_").upper()),
            "value": kwargs.get("value", cls.random_string("value_")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Constant')}"
            ),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "created_date": kwargs.get("created_date", cls.random_date().isoformat()),
        }

        return QTestPulseConstant(**constant_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseConstant]:
        """Create multiple qTest Pulse Constants."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseRuleFactory(MockFactory):
    """Factory for qTest Pulse Rule entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseRule:
        """Create a single qTest Pulse Rule."""
        # Create trigger and action if not provided
        project_id = kwargs.get("project_id", cls.random_id())

        if "trigger" not in kwargs and "trigger_id" not in kwargs:
            trigger = QTestPulseTriggerFactory.create(project_id=project_id)
            trigger_id = trigger.id
        elif "trigger" in kwargs:
            trigger = kwargs["trigger"]
            trigger_id = trigger.id
        else:
            trigger_id = kwargs["trigger_id"]

        if "action" not in kwargs and "action_id" not in kwargs:
            action = QTestPulseActionFactory.create(project_id=project_id)
            action_id = action.id
        elif "action" in kwargs:
            action = kwargs["action"]
            action_id = action.id
        else:
            action_id = kwargs["action_id"]

        rule_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Rule-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Rule')}"
            ),
            "project_id": project_id,
            "enabled": kwargs.get("enabled", True),
            "trigger_id": trigger_id,
            "action_id": action_id,
            "created_by": kwargs.get(
                "created_by", {"id": cls.random_id(), "name": cls.random_string("User-")}
            ),
            "created_date": kwargs.get("created_date", cls.random_date().isoformat()),
        }

        return QTestPulseRule(**rule_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseRule]:
        """Create multiple qTest Pulse Rules."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestScenarioFeatureFactory(MockFactory):
    """Factory for qTest Scenario Feature entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestScenarioFeature:
        """Create a single qTest Scenario Feature."""
        # Create feature content if not provided
        if "content" not in kwargs:
            feature_name = kwargs.get("name", cls.random_string("Feature-"))
            scenarios = []

            # Generate 1-3 scenarios
            for i in range(random.randint(1, 3)):
                scenario_name = f"Scenario {i+1}"
                steps = []

                # Generate steps
                steps.append(f"Given {cls.random_string('given_')}")
                steps.append(f"When {cls.random_string('when_')}")
                steps.append(f"Then {cls.random_string('then_')}")

                scenarios.append(
                    f"""
  Scenario: {scenario_name}
    {steps[0]}
    {steps[1]}
    {steps[2]}
                """
                )

            content = f"""
Feature: {feature_name}
  As a user
  I want to {cls.random_string('action_')}
  So that I can {cls.random_string('benefit_')}

{chr(10).join(scenarios)}
            """
        else:
            content = kwargs["content"]

        feature_data = {
            "id": kwargs.get("id", str(uuid.uuid4())),
            "name": kwargs.get("name", cls.random_string("Feature-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Feature')}"
            ),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "content": content,
        }

        return QTestScenarioFeature(**feature_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestScenarioFeature]:
        """Create multiple qTest Scenario Features."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestConfigFactory(MockFactory):
    """Factory for qTest API configuration."""

    @classmethod
    def create(cls, **kwargs) -> QTestConfig:
        """Create a single qTest API configuration."""
        config_data = {
            "base_url": kwargs.get("base_url", "https://example.qtest.com"),
            "username": kwargs.get("username", f"user_{cls.random_string()}"),
            "password": kwargs.get("password", cls.random_string("pass_")),
            "project_id": kwargs.get("project_id", cls.random_id()),
        }
        return QTestConfig(**config_data)


class QTestPaginatedResponseFactory(MockFactory):
    """Factory for qTest paginated API responses."""

    @classmethod
    def create(cls, **kwargs) -> QTestPaginatedResponse:
        """Create a single qTest paginated response."""
        # Create item dictionaries if not provided
        if "items" not in kwargs:
            item_count = kwargs.get("item_count", random.randint(1, 10))
            items = [
                {"id": cls.random_id(), "name": cls.random_string()} for _ in range(item_count)
            ]
        else:
            items = kwargs["items"]
            item_count = len(items)

        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        total = kwargs.get("total", item_count + random.randint(0, 20))

        response_data = {
            "items": items,
            "page": page,
            "page_size": page_size,
            "offset": kwargs.get("offset", (page - 1) * page_size),
            "limit": kwargs.get("limit", page_size),
            "total": total,
            "is_last": kwargs.get("is_last", page * page_size >= total),
        }
        return QTestPaginatedResponse(**response_data)


class QTestLinkFactory(MockFactory):
    """Factory for qTest link entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestLink:
        """Create a single qTest link."""
        link_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Link-")),
            "url": kwargs.get("url", f"https://example.com/{cls.random_string()}"),
            "icon_url": kwargs.get(
                "icon_url", f"https://example.com/icons/{cls.random_string()}.png"
            ),
            "target": kwargs.get("target", "_blank"),
        }
        return QTestLink(**link_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestLink]:
        """Create multiple qTest links."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestFieldFactory(MockFactory):
    """Factory for qTest field entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestField:
        """Create a single qTest field."""
        field_type = kwargs.get("field_type", cls.random_list_item(QTestField.VALID_FIELD_TYPES))
        entity_type = kwargs.get("entity_type", cls.random_list_item(QTestField.VALID_ENTITY_TYPES))

        field_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("field_")),
            "label": kwargs.get("label", cls.random_string("Field ")),
            "field_type": field_type,
            "entity_type": entity_type,
            "allowed_values": kwargs.get("allowed_values"),
            "required": kwargs.get("required", random.choice([True, False])),
        }
        return QTestField(**field_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestField]:
        """Create multiple qTest fields."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestAutomationSettingsFactory(MockFactory):
    """Factory for qTest automation settings."""

    @classmethod
    def create(cls, **kwargs) -> QTestAutomationSettings:
        """Create a single qTest automation settings object."""
        framework_id = kwargs.get("framework_id", cls.random_id())

        settings_data = {
            "automation_id": kwargs.get("automation_id", f"auto_{cls.random_string()}"),
            "framework_id": framework_id,
            "framework_name": kwargs.get("framework_name", cls.random_string("Framework-")),
            "parameters": kwargs.get(
                "parameters", {"param1": cls.random_string(), "param2": cls.random_string()}
            ),
            "is_parameterized": kwargs.get("is_parameterized", random.choice([True, False])),
            "external_id": kwargs.get("external_id", cls.random_string("ext_")),
        }
        return QTestAutomationSettings(**settings_data)


class QTestTestExecutionFactory(MockFactory):
    """Factory for qTest test execution entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestTestExecution:
        """Create a single qTest test execution."""
        execution_date = kwargs.get("execution_date", cls.random_date())
        status = kwargs.get("status", cls.random_list_item(QTestTestExecution.VALID_STATUSES))
        test_run_id = kwargs.get("test_run_id", cls.random_id())

        # Create test step logs if not provided
        if "test_step_logs" not in kwargs:
            step_count = random.randint(1, 5)
            step_logs = []
            for i in range(step_count):
                step_logs.append(
                    {
                        "stepId": i + 1,
                        "status": cls.random_list_item(QTestTestExecution.VALID_STATUSES),
                        "actualResult": f"Actual result for step {i+1}",
                        "executionNotes": f"Notes for step {i+1}",
                    }
                )
        else:
            step_logs = kwargs["test_step_logs"]

        execution_data = {
            "id": kwargs.get("id", cls.random_id()),
            "test_run_id": test_run_id,
            "status": status,
            "execution_date": execution_date,
            "executed_by": kwargs.get("executed_by", cls.random_id()),
            "note": kwargs.get("note", f"Execution completed with status: {status}"),
            "attachments": kwargs.get(
                "attachments", QTestAttachmentFactory.create_batch(random.randint(0, 2))
            ),
            "test_step_logs": step_logs,
            "build": kwargs.get("build", f"1.{random.randint(0, 10)}.{random.randint(0, 100)}"),
            "build_url": kwargs.get("build_url", f"https://ci.example.com/build/{cls.random_id()}"),
            "duration": kwargs.get("duration", random.randint(100, 10000)),
        }
        return QTestTestExecution(**execution_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestTestExecution]:
        """Create multiple qTest test executions."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseConditionFactory(MockFactory):
    """Factory for qTest Pulse condition entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseCondition:
        """Create a single qTest Pulse condition."""
        operator = kwargs.get("operator", cls.random_list_item(QTestPulseCondition.VALID_OPERATORS))

        # Select appropriate value based on operator
        if "value" not in kwargs:
            if operator in ["equals", "not_equals"]:
                value = cls.random_string()
            elif operator in ["contains", "not_contains", "starts_with", "ends_with"]:
                value = cls.random_string()
            elif operator in ["greater_than", "less_than"]:
                value = random.randint(1, 100)
            else:  # is_empty, is_not_empty
                value = None
        else:
            value = kwargs["value"]

        condition_data = {
            "field": kwargs.get("field", cls.random_string("field_")),
            "operator": operator,
            "value": value,
            "value_type": kwargs.get("value_type"),
        }
        return QTestPulseCondition(**condition_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseCondition]:
        """Create multiple qTest Pulse conditions."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseActionParameterFactory(MockFactory):
    """Factory for qTest Pulse action parameter entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestPulseActionParameter:
        """Create a single qTest Pulse action parameter."""
        # Default to string type for simplicity
        value_type = kwargs.get("value_type", "string")

        # Generate appropriate value based on type
        if "value" not in kwargs:
            if value_type == "string":
                value = cls.random_string("value_")
            elif value_type == "number":
                value = random.randint(1, 100)
            elif value_type == "boolean":
                value = random.choice([True, False])
            elif value_type == "array":
                value = [cls.random_string() for _ in range(random.randint(1, 3))]
            elif value_type == "object":
                value = {"key1": cls.random_string(), "key2": cls.random_string()}
            else:
                value = cls.random_string()
        else:
            value = kwargs["value"]

        parameter_data = {
            "name": kwargs.get("name", cls.random_string("param_")),
            "value": value,
            "value_type": value_type,
        }
        return QTestPulseActionParameter(**parameter_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestPulseActionParameter]:
        """Create multiple qTest Pulse action parameters."""
        return [cls.create(**kwargs) for _ in range(count)]
