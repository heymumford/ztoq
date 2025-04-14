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
    QTestCustomField,
    QTestDataset,
    QTestDatasetRow,
    QTestModule,
    QTestParameter,
    QTestParameterValue,
    QTestProject,
    QTestPulseAction,
    QTestPulseConstant,
    QTestPulseRule,
    QTestPulseTrigger,
    QTestRelease,
    QTestScenarioFeature,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
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

    FIELD_TYPES = ["STRING", "NUMBER", "DATE", "CHECKBOX", "USER", "RELEASE", "MULTI_SELECT"]

    @classmethod
    def create(cls, **kwargs) -> QTestCustomField:
        """Create a single qTest Custom Field."""
        field_type = kwargs.get("type", cls.random_list_item(cls.FIELD_TYPES))
        field_id = kwargs.get("id", cls.random_id())

        # Generate appropriate value based on type
        if "value" in kwargs:
            field_value = kwargs["value"]
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
            elif field_type == "RELEASE":
                field_value = cls.random_id()
            elif field_type == "MULTI_SELECT":
                field_value = ",".join(
                    [cls.random_string("Option-") for _ in range(random.randint(1, 3))]
                )
            else:
                field_value = cls.random_string("Value-")

        field_data = {
            "id": field_id,
            "name": kwargs.get("name", cls.random_string("Field-")),
            "type": field_type,
            "value": field_value,
            "required": kwargs.get("required", False),
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

        test_case_data = {
            "id": test_case_id,
            "pid": kwargs.get("pid", f"TC-{test_case_id}"),
            "name": kwargs.get("name", cls.random_string("Test Case-")),
            "description": kwargs.get(
                "description", f"Description for test case {kwargs.get('name', 'Test Case')}"
            ),
            "precondition": kwargs.get("precondition", "Test case precondition"),
            "test_steps": kwargs.get("test_steps", QTestStepFactory.create_batch(3)),
            "properties": kwargs.get("properties", QTestCustomFieldFactory.create_batch(2)),
            "parent_id": kwargs.get("parent_id"),
            "module_id": kwargs.get("module_id", cls.random_id()),
            "priority_id": kwargs.get("priority_id", random.randint(1, 5)),
            "creator_id": kwargs.get("creator_id", cls.random_id()),
            "attachments": kwargs.get("attachments", []),
            "create_date": create_date,
            "last_modified_date": kwargs.get("last_modified_date", create_date),
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

        run_data = {
            "id": run_id,
            "name": kwargs.get("name", run_name),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', run_name)}"
            ),
            "pid": kwargs.get("pid", f"TR-{run_id}"),
            "test_case_version_id": kwargs.get("test_case_version_id", 1),
            "test_case_id": test_case_id,
            "test_cycle_id": kwargs.get("test_cycle_id", cls.random_id()),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "properties": kwargs.get("properties", QTestCustomFieldFactory.create_batch(2)),
            "status": kwargs.get("status", "NOT_EXECUTED"),
        }

        return QTestTestRun(**run_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestTestRun]:
        """Create multiple qTest Test Runs."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestTestLogFactory(MockFactory):
    """Factory for qTest Test Log entities."""

    TEST_STATUSES = ["PASS", "FAIL", "BLOCKED", "INCOMPLETE", "NOT_EXECUTED"]

    @classmethod
    def create(cls, **kwargs) -> QTestTestLog:
        """Create a single qTest Test Log."""
        status = kwargs.get("status", cls.random_list_item(cls.TEST_STATUSES))

        log_data = {
            "id": kwargs.get("id", cls.random_id()),
            "status": status,
            "execution_date": kwargs.get("execution_date", cls.random_date(10)),
            "note": kwargs.get("note", f"Test executed with result: {status}"),
            "attachments": kwargs.get("attachments", []),
            "properties": kwargs.get("properties", QTestCustomFieldFactory.create_batch(1)),
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


class QTestParameterFactory(MockFactory):
    """Factory for qTest Parameter entities."""

    @classmethod
    def create(cls, **kwargs) -> QTestParameter:
        """Create a single qTest Parameter."""
        param_id = kwargs.get("id", cls.random_id())

        # Create parameter values if not provided
        if "values" not in kwargs:
            values = [
                QTestParameterValue(id=cls.random_id(), value=f"Value-{i+1}", parameter_id=param_id)
                for i in range(random.randint(2, 5))
            ]
        else:
            values = kwargs["values"]

        param_data = {
            "id": param_id,
            "name": kwargs.get("name", cls.random_string("Parameter-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Parameter')}"
            ),
            "project_id": kwargs.get("project_id", cls.random_id()),
            "status": kwargs.get("status", "ACTIVE"),
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

        # Create rows if not provided
        if "rows" not in kwargs:
            # Generate column names
            columns = kwargs.get("columns", ["column1", "column2", "column3"])

            # Generate 2-5 rows of data
            rows = []
            for i in range(random.randint(2, 5)):
                row_values = {col: f"Value-{i+1}-{col}" for col in columns}
                rows.append(
                    QTestDatasetRow(id=cls.random_id(), dataset_id=dataset_id, values=row_values)
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
            "status": kwargs.get("status", "ACTIVE"),
            "rows": rows,
        }

        return QTestDataset(**dataset_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> List[QTestDataset]:
        """Create multiple qTest Datasets."""
        return [cls.create(**kwargs) for _ in range(count)]


class QTestPulseTriggerFactory(MockFactory):
    """Factory for qTest Pulse Trigger entities."""

    EVENT_TYPES = [
        "TEST_CASE_CREATED",
        "TEST_CASE_UPDATED",
        "TEST_CYCLE_CREATED",
        "TEST_LOG_CREATED",
        "DEFECT_CREATED",
        "REQUIREMENT_CREATED",
    ]

    @classmethod
    def create(cls, **kwargs) -> QTestPulseTrigger:
        """Create a single qTest Pulse Trigger."""
        event_type = kwargs.get("event_type", cls.random_list_item(cls.EVENT_TYPES))

        # Create conditions if not provided
        if "conditions" not in kwargs:
            # Generate 0-3 conditions
            conditions = []
            for _ in range(random.randint(0, 3)):
                conditions.append(
                    {
                        "field": cls.random_string("field_"),
                        "operator": cls.random_list_item(
                            ["equals", "contains", "startsWith", "endsWith"]
                        ),
                        "value": cls.random_string("value_"),
                    }
                )
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

    ACTION_TYPES = [
        "CREATE_DEFECT",
        "SEND_MAIL",
        "UPDATE_FIELD_VALUE",
        "WEBHOOK",
        "UPDATE_TEST_RUN_STATUS",
    ]

    @classmethod
    def create(cls, **kwargs) -> QTestPulseAction:
        """Create a single qTest Pulse Action."""
        action_type = kwargs.get("action_type", cls.random_list_item(cls.ACTION_TYPES))

        # Create parameters if not provided
        if "parameters" not in kwargs:
            # Generate parameters based on action type
            parameters = []
            if action_type == "CREATE_DEFECT":
                parameters = [
                    {"name": "issueType", "value": "Bug"},
                    {"name": "summary", "value": "{{testCase.name}} failed"},
                    {"name": "description", "value": "Failure in {{testCase.name}}"},
                ]
            elif action_type == "SEND_MAIL":
                parameters = [
                    {"name": "recipients", "value": "test@example.com"},
                    {"name": "subject", "value": "Test Notification: {{testCase.name}}"},
                    {"name": "body", "value": "Test case {{testCase.name}} has been updated."},
                ]
            elif action_type == "UPDATE_FIELD":
                parameters = [
                    {"name": "fieldId", "value": cls.random_id()},
                    {"name": "value", "value": "New Value"},
                ]
            else:
                # Generic parameters
                parameters = [
                    {"name": "param1", "value": "value1"},
                    {"name": "param2", "value": "value2"},
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
        """Create multiple qTest Pulse Actions."""
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

        if "trigger_id" not in kwargs:
            trigger = QTestPulseTriggerFactory.create(project_id=project_id)
            trigger_id = trigger.id
        else:
            trigger_id = kwargs["trigger_id"]

        if "action_id" not in kwargs:
            action = QTestPulseActionFactory.create(project_id=project_id)
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
