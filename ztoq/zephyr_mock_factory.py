"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Mock factory for generating Zephyr entity objects.

This module provides factories for generating mock Zephyr entities for testing.
Each factory can generate individual entities or collections of entities.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

from ztoq.models import (
    Attachment,
    Case,
    CaseStep,
    CustomField,
    CustomFieldType,
    CycleInfo,
    Environment,
    Execution,
    Folder,
    Link,
    PaginatedResponse,
    Plan,
    Priority,
    Project,
    Status,
    ZephyrConfig,
)


class MockFactory:
    """Base class for all mock factories with common utility methods."""

    @staticmethod
    def random_id() -> str:
        """Generate a random ID."""
        return str(random.randint(1000, 9999))

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
    def random_list_item(items: list[Any]) -> Any:
        """Choose a random item from a list."""
        return random.choice(items)

    @staticmethod
    def dict_to_model(model_class: Any, data: dict[str, Any]) -> BaseModel:
        """Convert a dictionary to a Pydantic model instance."""
        return model_class(**data)


class ProjectFactory(MockFactory):
    """Factory for Zephyr Project entities."""

    @classmethod
    def create(cls, **kwargs) -> Project:
        """Create a single Zephyr Project."""
        project_data = {
            "id": kwargs.get("id", cls.random_id()),
            "key": kwargs.get("key", cls.random_string("PROJ-")),
            "name": kwargs.get("name", cls.random_string("Project-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Project')}",
            ),
        }
        return Project(**project_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> list[Project]:
        """Create multiple Zephyr Projects."""
        return [cls.create(**kwargs) for _ in range(count)]


class FolderFactory(MockFactory):
    """Factory for Zephyr Folder entities."""

    @classmethod
    def create(cls, **kwargs) -> Folder:
        """Create a single Zephyr Folder."""
        folder_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Folder-")),
            "folder_type": kwargs.get("folder_type", random.choice(["TEST_CASE", "TEST_CYCLE"])),
            "parent_id": kwargs.get("parent_id"),
            "project_key": kwargs.get("project_key", cls.random_string("PROJ-")),
        }
        return Folder(**folder_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> list[Folder]:
        """Create multiple Zephyr Folders."""
        return [cls.create(**kwargs) for _ in range(count)]


class PriorityFactory(MockFactory):
    """Factory for Zephyr Priority entities."""

    @classmethod
    def create(cls, **kwargs) -> Priority:
        """Create a single Zephyr Priority."""
        priority_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", random.choice(["High", "Medium", "Low"])),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Priority')}",
            ),
            "color": kwargs.get("color", random.choice(["#ff0000", "#00ff00", "#0000ff"])),
            "rank": kwargs.get("rank", random.randint(1, 5)),
        }
        return Priority(**priority_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Priority]:
        """Create multiple Zephyr Priorities."""
        return [cls.create(**kwargs) for _ in range(count)]


class StatusFactory(MockFactory):
    """Factory for Zephyr Status entities."""

    @classmethod
    def create(cls, **kwargs) -> Status:
        """Create a single Zephyr Status."""
        status_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", random.choice(["Active", "Draft", "Deprecated"])),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Status')}",
            ),
            "color": kwargs.get("color", random.choice(["#ffff00", "#00ffff", "#ff00ff"])),
            "type": kwargs.get(
                "type", random.choice(["TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION"]),
            ),
        }
        return Status(**status_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Status]:
        """Create multiple Zephyr Statuses."""
        return [cls.create(**kwargs) for _ in range(count)]


class EnvironmentFactory(MockFactory):
    """Factory for Zephyr Environment entities."""

    @classmethod
    def create(cls, **kwargs) -> Environment:
        """Create a single Zephyr Environment."""
        environment_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Environment-")),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Environment')}",
            ),
        }
        return Environment(**environment_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Environment]:
        """Create multiple Zephyr Environments."""
        return [cls.create(**kwargs) for _ in range(count)]


class CustomFieldFactory(MockFactory):
    """Factory for Zephyr CustomField entities."""

    @classmethod
    def create(cls, **kwargs) -> CustomField:
        """Create a single Zephyr CustomField."""
        field_type = kwargs.get("type", cls.random_enum(CustomFieldType))

        # Generate appropriate value based on type
        if "value" in kwargs:
            field_value = kwargs["value"]
        elif field_type == CustomFieldType.TEXT:
            field_value = cls.random_string("Text-")
        elif field_type == CustomFieldType.PARAGRAPH:
            field_value = cls.random_string("Paragraph-") * 3
        elif field_type == CustomFieldType.CHECKBOX:
            field_value = cls.random_bool()
        elif field_type == CustomFieldType.NUMERIC:
            field_value = random.randint(1, 100)
        elif field_type == CustomFieldType.DATE:
            field_value = cls.random_date().strftime("%Y-%m-%d")
        elif field_type == CustomFieldType.DATETIME:
            field_value = cls.random_date().isoformat()
        elif field_type in [CustomFieldType.RADIO, CustomFieldType.DROPDOWN]:
            field_value = cls.random_string("Option-")
        elif field_type == CustomFieldType.MULTIPLE_SELECT:
            field_value = [cls.random_string("Option-") for _ in range(random.randint(1, 3))]
        else:
            field_value = cls.random_string("Value-")

        field_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Field-")),
            "type": field_type,
            "value": field_value,
        }

        return CustomField(**field_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[CustomField]:
        """Create multiple Zephyr CustomFields."""
        return [cls.create(**kwargs) for _ in range(count)]


class LinkFactory(MockFactory):
    """Factory for Zephyr Link entities."""

    @classmethod
    def create(cls, **kwargs) -> Link:
        """Create a single Zephyr Link."""
        link_data = {
            "id": kwargs.get("id", cls.random_id()),
            "name": kwargs.get("name", cls.random_string("Link-")),
            "url": kwargs.get("url", f"https://example.com/{cls.random_string()}"),
            "description": kwargs.get(
                "description", f"Description for {kwargs.get('name', 'Link')}",
            ),
            "type": kwargs.get("type", random.choice(["issue", "web", "testCycle"])),
        }
        return Link(**link_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Link]:
        """Create multiple Zephyr Links."""
        return [cls.create(**kwargs) for _ in range(count)]


class AttachmentFactory(MockFactory):
    """Factory for Zephyr Attachment entities."""

    @classmethod
    def create(cls, **kwargs) -> Attachment:
        """Create a single Zephyr Attachment."""
        content_type = kwargs.get(
            "content_type",
            random.choice(
                ["image/png", "image/jpeg", "application/pdf", "text/plain", "application/json"],
            ),
        )

        extension = content_type.split("/")[-1]
        if extension == "jpeg":
            extension = "jpg"

        attachment_data = {
            "id": kwargs.get("id", cls.random_id()),
            "filename": kwargs.get("filename", f"{cls.random_string()}.{extension}"),
            "content_type": content_type,
            "size": kwargs.get("size", random.randint(1024, 1048576)),  # 1KB to 1MB
            "created_on": kwargs.get("created_on", cls.random_date()),
            "created_by": kwargs.get("created_by", cls.random_string("User-")),
            "content": kwargs.get("content"),
        }
        return Attachment(**attachment_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Attachment]:
        """Create multiple Zephyr Attachments."""
        return [cls.create(**kwargs) for _ in range(count)]


class CaseStepFactory(MockFactory):
    """Factory for Zephyr CaseStep entities."""

    @classmethod
    def create(cls, **kwargs) -> CaseStep:
        """Create a single Zephyr CaseStep."""
        step_data = {
            "id": kwargs.get("id", cls.random_id()),
            "index": kwargs.get("index", random.randint(1, 10)),
            "description": kwargs.get(
                "description", f"Step {kwargs.get('index', 1)}: {cls.random_string()}",
            ),
            "expected_result": kwargs.get(
                "expected_result", f"Expected result for step {kwargs.get('index', 1)}",
            ),
            "data": kwargs.get("data"),
            "actual_result": kwargs.get("actual_result"),
            "status": kwargs.get("status"),
            "attachments": kwargs.get("attachments", []),
        }
        return CaseStep(**step_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[CaseStep]:
        """Create multiple Zephyr CaseSteps with sequential indexes."""
        return [cls.create(index=i + 1, **kwargs) for i in range(count)]


class CaseFactory(MockFactory):
    """Factory for Zephyr Case entities."""

    @classmethod
    def create(cls, **kwargs) -> Case:
        """Create a single Zephyr Case."""
        case_id = kwargs.get("id", cls.random_id())
        project_key = kwargs.get("project_key", "PROJ")
        key = kwargs.get("key", f"{project_key}-T{random.randint(100, 999)}")

        # Create steps if not provided
        if "steps" not in kwargs:
            steps = CaseStepFactory.create_batch(random.randint(1, 5))
        else:
            steps = kwargs["steps"]

        # Create priority if not provided
        if "priority" not in kwargs:
            priority = PriorityFactory.create()
        else:
            priority = kwargs["priority"]

        case_data = {
            "id": case_id,
            "key": key,
            "name": kwargs.get("name", cls.random_string("Test Case ")),
            "objective": kwargs.get("objective", f"Objective for {key}"),
            "precondition": kwargs.get("precondition", f"Precondition for {key}"),
            "description": kwargs.get("description", f"Description for {key}"),
            "status": kwargs.get("status", random.choice(["Active", "Draft", "Deprecated"])),
            "priority": priority,
            "priority_name": kwargs.get("priority_name", priority.name if priority else None),
            "folder": kwargs.get("folder", cls.random_id()),
            "folder_name": kwargs.get("folder_name", cls.random_string("Folder-")),
            "owner": kwargs.get("owner", cls.random_id()),
            "owner_name": kwargs.get("owner_name", cls.random_string("User-")),
            "component": kwargs.get("component"),
            "component_name": kwargs.get("component_name"),
            "created_on": kwargs.get("created_on", cls.random_date()),
            "created_by": kwargs.get("created_by", cls.random_id()),
            "updated_on": kwargs.get("updated_on", cls.random_date()),
            "updated_by": kwargs.get("updated_by", cls.random_id()),
            "version": kwargs.get("version", "1.0"),
            "estimated_time": kwargs.get(
                "estimated_time", random.randint(15, 240) * 60,
            ),  # 15-240 minutes in seconds
            "labels": kwargs.get(
                "labels", [cls.random_string("Label-") for _ in range(random.randint(0, 3))],
            ),
            "steps": steps,
            "custom_fields": kwargs.get("custom_fields", []),
            "links": kwargs.get("links", []),
            "scripts": kwargs.get("scripts", []),
            "versions": kwargs.get("versions", []),
            "attachments": kwargs.get("attachments", []),
        }
        return Case(**case_data)

    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> list[Case]:
        """Create multiple Zephyr Cases."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_with_steps(cls, step_count: int = 3, **kwargs) -> Case:
        """
        Create a Case with the specified number of steps.

        Args:
            step_count: Number of steps to create
            **kwargs: Additional fields to override

        Returns:
            Case: Created model instance with steps

        """
        # Create the steps
        steps = CaseStepFactory.create_batch(step_count)

        # Add steps to kwargs
        if "steps" not in kwargs:
            kwargs["steps"] = steps

        # Create the test case
        return cls.create(**kwargs)


class CycleInfoFactory(MockFactory):
    """Factory for Zephyr CycleInfo entities."""

    @classmethod
    def create(cls, **kwargs) -> CycleInfo:
        """Create a single Zephyr CycleInfo."""
        cycle_id = kwargs.get("id", cls.random_id())
        project_key = kwargs.get("project_key", "PROJ")
        key = kwargs.get("key", f"{project_key}-C{random.randint(100, 999)}")

        cycle_data = {
            "id": cycle_id,
            "key": key,
            "name": kwargs.get("name", cls.random_string("Test Cycle ")),
            "description": kwargs.get("description", f"Description for {key}"),
            "status": kwargs.get("status", random.choice(["Active", "Draft", "Completed"])),
            "status_name": kwargs.get("status_name"),
            "folder": kwargs.get("folder", cls.random_id()),
            "folder_name": kwargs.get("folder_name", cls.random_string("Folder-")),
            "project_key": project_key,
            "owner": kwargs.get("owner", cls.random_id()),
            "owner_name": kwargs.get("owner_name", cls.random_string("User-")),
            "created_on": kwargs.get("created_on", cls.random_date()),
            "created_by": kwargs.get("created_by", cls.random_id()),
            "updated_on": kwargs.get("updated_on", cls.random_date()),
            "updated_by": kwargs.get("updated_by", cls.random_id()),
            "custom_fields": kwargs.get("custom_fields", []),
            "links": kwargs.get("links", []),
            "attachments": kwargs.get("attachments", []),
        }
        return CycleInfo(**cycle_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[CycleInfo]:
        """Create multiple Zephyr CycleInfos."""
        return [cls.create(**kwargs) for _ in range(count)]


class PlanFactory(MockFactory):
    """Factory for Zephyr Plan entities."""

    @classmethod
    def create(cls, **kwargs) -> Plan:
        """Create a single Zephyr Plan."""
        plan_id = kwargs.get("id", cls.random_id())
        project_key = kwargs.get("project_key", "PROJ")
        key = kwargs.get("key", f"{project_key}-P{random.randint(100, 999)}")

        plan_data = {
            "id": plan_id,
            "key": key,
            "name": kwargs.get("name", cls.random_string("Test Plan ")),
            "description": kwargs.get("description", f"Description for {key}"),
            "status": kwargs.get("status", random.choice(["Active", "Draft", "Completed"])),
            "status_name": kwargs.get("status_name"),
            "folder": kwargs.get("folder", cls.random_id()),
            "folder_name": kwargs.get("folder_name", cls.random_string("Folder-")),
            "project_key": project_key,
            "owner": kwargs.get("owner", cls.random_id()),
            "owner_name": kwargs.get("owner_name", cls.random_string("User-")),
            "created_on": kwargs.get("created_on", cls.random_date()),
            "created_by": kwargs.get("created_by", cls.random_id()),
            "updated_on": kwargs.get("updated_on", cls.random_date()),
            "updated_by": kwargs.get("updated_by", cls.random_id()),
            "custom_fields": kwargs.get("custom_fields", []),
            "links": kwargs.get("links", []),
        }
        return Plan(**plan_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Plan]:
        """Create multiple Zephyr Plans."""
        return [cls.create(**kwargs) for _ in range(count)]


class ExecutionFactory(MockFactory):
    """Factory for Zephyr Execution entities."""

    @classmethod
    def create(cls, **kwargs) -> Execution:
        """Create a single Zephyr Execution."""
        execution_id = kwargs.get("id", cls.random_id())
        test_case_key = kwargs.get("test_case_key", f"PROJ-T{random.randint(100, 999)}")

        # Create steps if not provided, basing them on test case if provided
        if "steps" not in kwargs:
            if "test_case" in kwargs:
                test_case = kwargs["test_case"]
                steps = []
                for case_step in test_case.steps:
                    # Create an execution step based on the test case step
                    execution_step = CaseStepFactory.create(
                        id=case_step.id,
                        index=case_step.index,
                        description=case_step.description,
                        expected_result=case_step.expected_result,
                        data=case_step.data,
                        status=random.choice(["Passed", "Failed", "Blocked", "Not Run"]),
                        actual_result=f"Actual result for step {case_step.index}",
                    )
                    steps.append(execution_step)
            else:
                steps = CaseStepFactory.create_batch(random.randint(1, 5))
        else:
            steps = kwargs["steps"]

        execution_data = {
            "id": execution_id,
            "test_case_key": test_case_key,
            "cycle_id": kwargs.get("cycle_id", cls.random_id()),
            "cycle_name": kwargs.get("cycle_name", cls.random_string("Cycle-")),
            "status": kwargs.get(
                "status", random.choice(["Passed", "Failed", "Blocked", "Not Run"]),
            ),
            "status_name": kwargs.get("status_name"),
            "environment": kwargs.get("environment", cls.random_id()),
            "environment_name": kwargs.get("environment_name", cls.random_string("Environment-")),
            "executed_by": kwargs.get("executed_by", cls.random_id()),
            "executed_by_name": kwargs.get("executed_by_name", cls.random_string("User-")),
            "executed_on": kwargs.get("executed_on", cls.random_date()),
            "created_on": kwargs.get("created_on", cls.random_date()),
            "created_by": kwargs.get("created_by", cls.random_id()),
            "updated_on": kwargs.get("updated_on", cls.random_date()),
            "updated_by": kwargs.get("updated_by", cls.random_id()),
            "actual_time": kwargs.get(
                "actual_time", random.randint(300, 7200),
            ),  # 5-120 minutes in seconds
            "comment": kwargs.get("comment", f"Execution comments for {test_case_key}"),
            "steps": steps,
            "custom_fields": kwargs.get("custom_fields", []),
            "links": kwargs.get("links", []),
            "attachments": kwargs.get("attachments", []),
        }
        return Execution(**execution_data)

    @classmethod
    def create_batch(cls, count: int = 3, **kwargs) -> list[Execution]:
        """Create multiple Zephyr Executions."""
        return [cls.create(**kwargs) for _ in range(count)]


class ZephyrConfigFactory(MockFactory):
    """Factory for ZephyrConfig configuration."""

    @classmethod
    def create(cls, **kwargs) -> ZephyrConfig:
        """Create a single ZephyrConfig."""
        config_data = {
            "base_url": kwargs.get("base_url", "https://api.example.zephyrscale.com/v2"),
            "api_token": kwargs.get("api_token", f"token-{cls.random_string()}"),
            "project_key": kwargs.get("project_key", cls.random_string("PROJ-")),
        }
        return ZephyrConfig(**config_data)


class PaginatedResponseFactory(MockFactory):
    """Factory for Zephyr paginated API responses."""

    @classmethod
    def create(cls, **kwargs) -> PaginatedResponse:
        """Create a single Zephyr paginated response."""
        # Create items if not provided
        if "values" not in kwargs:
            item_count = kwargs.get("item_count", random.randint(1, 10))
            values = [
                {"id": cls.random_id(), "name": cls.random_string()} for _ in range(item_count)
            ]
        else:
            values = kwargs["values"]
            item_count = len(values)

        max_results = kwargs.get("max_results", 20)
        start_at = kwargs.get("start_at", 0)
        total_count = kwargs.get("total_count", item_count + random.randint(0, 20))

        # Determine if this is the last page
        is_last = kwargs.get("is_last", (start_at + item_count) >= total_count)

        response_data = {
            "values": values,
            "start_at": start_at,
            "max_results": max_results,
            "total_count": total_count,
            "is_last": is_last,
        }
        return PaginatedResponse(**response_data)
