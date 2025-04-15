"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from datetime import datetime, timedelta
from ztoq.zephyr_mock_factory import (
    MockFactory,
    AttachmentFactory,
    CaseFactory,
    CaseStepFactory,
    CustomFieldFactory,
    CycleInfoFactory,
    EnvironmentFactory,
    ExecutionFactory,
    FolderFactory,
    LinkFactory,
    PaginatedResponseFactory,
    PlanFactory,
    PriorityFactory,
    ProjectFactory,
    StatusFactory,
    ZephyrConfigFactory,
)
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


@pytest.mark.unit()
class TestZephyrMockFactory:
    """Test suite for the Zephyr mock factory implementations."""

    def test_base_mock_factory(self):
        """Test the base MockFactory utility methods."""
        # Test random ID generation
        random_id = MockFactory.random_id()
        assert isinstance(random_id, str)
        assert random_id.isdigit()

        # Test random string generation
        random_string = MockFactory.random_string()
        assert isinstance(random_string, str)
        assert len(random_string) == 8

        # Test random date generation
        random_date = MockFactory.random_date()
        assert isinstance(random_date, datetime)
        assert random_date <= datetime.now()

        # Test random boolean generation
        random_bool = MockFactory.random_bool()
        assert isinstance(random_bool, bool)

        # Test random list item selection
        items = [1, 2, 3, 4, 5]
        random_item = MockFactory.random_list_item(items)
        assert random_item in items

    def test_project_factory(self):
        """Test the ProjectFactory."""
        # Test single project creation
        project = ProjectFactory.create()
        assert project.id is not None
        assert project.key is not None
        assert project.name is not None
        assert project.description is not None
        assert isinstance(project, Project)

        # Test project creation with custom attributes
        custom_project = ProjectFactory.create(
            id="12345", key="CUSTOM", name="Custom Project", description="Custom description"
        )
        assert custom_project.id == "12345"
        assert custom_project.key == "CUSTOM"
        assert custom_project.name == "Custom Project"
        assert custom_project.description == "Custom description"

        # Test batch creation
        batch_size = 5
        projects = ProjectFactory.create_batch(batch_size)
        assert len(projects) == batch_size
        assert all(p.id is not None for p in projects)
        assert len(set(p.id for p in projects)) == batch_size  # Unique IDs

    def test_folder_factory(self):
        """Test the FolderFactory."""
        # Test single folder creation
        folder = FolderFactory.create()
        assert folder.id is not None
        assert folder.name is not None
        assert folder.folder_type in ["TEST_CASE", "TEST_CYCLE"]
        assert folder.project_key is not None
        assert isinstance(folder, Folder)

        # Test folder creation with custom attributes
        custom_folder = FolderFactory.create(
            id="12345",
            name="Custom Folder",
            folder_type="TEST_CASE",
            parent_id="54321",
            project_key="PROJ",
        )
        assert custom_folder.id == "12345"
        assert custom_folder.name == "Custom Folder"
        assert custom_folder.folder_type == "TEST_CASE"
        assert custom_folder.parent_id == "54321"
        assert custom_folder.project_key == "PROJ"

        # Test batch creation
        batch_size = 5
        folders = FolderFactory.create_batch(batch_size)
        assert len(folders) == batch_size
        assert all(f.id is not None for f in folders)
        assert len(set(f.id for f in folders)) == batch_size  # Unique IDs

    def test_priority_factory(self):
        """Test the PriorityFactory."""
        # Test single priority creation
        priority = PriorityFactory.create()
        assert priority.id is not None
        assert priority.name is not None
        assert priority.description is not None
        assert priority.color is not None
        assert priority.rank is not None
        assert isinstance(priority, Priority)

        # Test batch creation
        batch_size = 3
        priorities = PriorityFactory.create_batch(batch_size)
        assert len(priorities) == batch_size
        assert all(p.id is not None for p in priorities)
        assert len(set(p.id for p in priorities)) == batch_size  # Unique IDs

    def test_status_factory(self):
        """Test the StatusFactory."""
        # Test single status creation
        status = StatusFactory.create()
        assert status.id is not None
        assert status.name is not None
        assert status.description is not None
        assert status.color is not None
        assert status.type is not None
        assert isinstance(status, Status)

        # Test custom status creation
        custom_status = StatusFactory.create(id="12345", name="Custom Status", type="TEST_CASE")
        assert custom_status.id == "12345"
        assert custom_status.name == "Custom Status"
        assert custom_status.type == "TEST_CASE"

        # Test batch creation
        batch_size = 3
        statuses = StatusFactory.create_batch(batch_size)
        assert len(statuses) == batch_size
        assert all(s.id is not None for s in statuses)
        assert len(set(s.id for s in statuses)) == batch_size  # Unique IDs

    def test_environment_factory(self):
        """Test the EnvironmentFactory."""
        # Test single environment creation
        environment = EnvironmentFactory.create()
        assert environment.id is not None
        assert environment.name is not None
        assert environment.description is not None
        assert isinstance(environment, Environment)

        # Test batch creation
        batch_size = 3
        environments = EnvironmentFactory.create_batch(batch_size)
        assert len(environments) == batch_size
        assert all(e.id is not None for e in environments)
        assert len(set(e.id for e in environments)) == batch_size  # Unique IDs

    def test_custom_field_factory(self):
        """Test the CustomFieldFactory."""
        # Test TEXT custom field
        text_field = CustomFieldFactory.create(type=CustomFieldType.TEXT)
        assert text_field.id is not None
        assert text_field.name is not None
        assert text_field.type == CustomFieldType.TEXT
        assert isinstance(text_field.value, str)
        assert isinstance(text_field, CustomField)

        # Test CHECKBOX custom field
        checkbox_field = CustomFieldFactory.create(type=CustomFieldType.CHECKBOX)
        assert checkbox_field.id is not None
        assert checkbox_field.type == CustomFieldType.CHECKBOX
        assert isinstance(checkbox_field.value, bool)

        # Test NUMERIC custom field
        numeric_field = CustomFieldFactory.create(type=CustomFieldType.NUMERIC)
        assert numeric_field.id is not None
        assert numeric_field.type == CustomFieldType.NUMERIC
        assert isinstance(numeric_field.value, int)

        # Test MULTIPLE_SELECT custom field
        multiselect_field = CustomFieldFactory.create(type=CustomFieldType.MULTIPLE_SELECT)
        assert multiselect_field.id is not None
        assert multiselect_field.type == CustomFieldType.MULTIPLE_SELECT
        assert isinstance(multiselect_field.value, list)

        # Test batch creation
        batch_size = 3
        custom_fields = CustomFieldFactory.create_batch(batch_size)
        assert len(custom_fields) == batch_size
        assert all(cf.id is not None for cf in custom_fields)
        assert len(set(cf.id for cf in custom_fields)) == batch_size  # Unique IDs

    def test_link_factory(self):
        """Test the LinkFactory."""
        # Test single link creation
        link = LinkFactory.create()
        assert link.id is not None
        assert link.name is not None
        assert link.url is not None
        assert link.description is not None
        assert link.type is not None
        assert isinstance(link, Link)

        # Test batch creation
        batch_size = 3
        links = LinkFactory.create_batch(batch_size)
        assert len(links) == batch_size
        assert all(l.id is not None for l in links)
        assert len(set(l.id for l in links)) == batch_size  # Unique IDs

    def test_attachment_factory(self):
        """Test the AttachmentFactory."""
        # Test single attachment creation
        attachment = AttachmentFactory.create()
        assert attachment.id is not None
        assert attachment.filename is not None
        assert attachment.content_type is not None
        assert attachment.size is not None
        assert attachment.created_on is not None
        assert attachment.created_by is not None
        assert isinstance(attachment, Attachment)

        # Test specific content type
        pdf_attachment = AttachmentFactory.create(content_type="application/pdf")
        assert pdf_attachment.content_type == "application/pdf"
        assert pdf_attachment.filename.endswith(".pdf")

        # Test batch creation
        batch_size = 3
        attachments = AttachmentFactory.create_batch(batch_size)
        assert len(attachments) == batch_size
        assert all(a.id is not None for a in attachments)
        assert len(set(a.id for a in attachments)) == batch_size  # Unique IDs

    def test_case_step_factory(self):
        """Test the CaseStepFactory."""
        # Test single step creation
        step = CaseStepFactory.create()
        assert step.id is not None
        assert step.index is not None
        assert step.description is not None
        assert step.expected_result is not None
        assert isinstance(step, CaseStep)

        # Test step creation with specific index
        indexed_step = CaseStepFactory.create(index=5)
        assert indexed_step.index == 5
        assert "Step 5" in indexed_step.description

        # Test batch creation with sequential indexes
        steps = CaseStepFactory.create_batch(3)
        assert len(steps) == 3
        assert [s.index for s in steps] == [1, 2, 3]

    def test_case_factory(self):
        """Test the CaseFactory."""
        # Test single case creation
        case = CaseFactory.create()
        assert case.id is not None
        assert case.key is not None
        assert case.name is not None
        assert case.objective is not None
        assert case.precondition is not None
        assert case.description is not None
        assert case.status is not None
        assert case.priority is not None
        assert case.folder is not None
        assert case.folder_name is not None
        assert case.created_on is not None
        assert case.updated_on is not None
        assert len(case.steps) > 0
        assert isinstance(case, Case)

        # Test creation with custom steps
        custom_steps = CaseStepFactory.create_batch(2)
        case_with_steps = CaseFactory.create(steps=custom_steps)
        assert len(case_with_steps.steps) == 2
        assert case_with_steps.steps == custom_steps

        # Test batch creation
        batch_size = 3
        cases = CaseFactory.create_batch(batch_size)
        assert len(cases) == batch_size
        assert all(c.id is not None for c in cases)
        assert len(set(c.id for c in cases)) == batch_size  # Unique IDs

    def test_cycle_info_factory(self):
        """Test the CycleInfoFactory."""
        # Test single cycle creation
        cycle = CycleInfoFactory.create()
        assert cycle.id is not None
        assert cycle.key is not None
        assert cycle.name is not None
        assert cycle.description is not None
        assert cycle.status is not None
        assert cycle.folder is not None
        assert cycle.folder_name is not None
        assert cycle.project_key is not None
        assert cycle.created_on is not None
        assert cycle.updated_on is not None
        assert isinstance(cycle, CycleInfo)

        # Test cycle with specific project key
        project_cycle = CycleInfoFactory.create(project_key="PROJ1")
        assert project_cycle.project_key == "PROJ1"
        assert "PROJ1-C" in project_cycle.key

        # Test batch creation
        batch_size = 3
        cycles = CycleInfoFactory.create_batch(batch_size)
        assert len(cycles) == batch_size
        assert all(c.id is not None for c in cycles)
        assert len(set(c.id for c in cycles)) == batch_size  # Unique IDs

    def test_plan_factory(self):
        """Test the PlanFactory."""
        # Test single plan creation
        plan = PlanFactory.create()
        assert plan.id is not None
        assert plan.key is not None
        assert plan.name is not None
        assert plan.description is not None
        assert plan.status is not None
        assert plan.folder is not None
        assert plan.folder_name is not None
        assert plan.project_key is not None
        assert plan.created_on is not None
        assert plan.updated_on is not None
        assert isinstance(plan, Plan)

        # Test plan with specific project key
        project_plan = PlanFactory.create(project_key="PROJ1")
        assert project_plan.project_key == "PROJ1"
        assert "PROJ1-P" in project_plan.key

        # Test batch creation
        batch_size = 3
        plans = PlanFactory.create_batch(batch_size)
        assert len(plans) == batch_size
        assert all(p.id is not None for p in plans)
        assert len(set(p.id for p in plans)) == batch_size  # Unique IDs

    def test_execution_factory(self):
        """Test the ExecutionFactory."""
        # Test single execution creation
        execution = ExecutionFactory.create()
        assert execution.id is not None
        assert execution.test_case_key is not None
        assert execution.cycle_id is not None
        assert execution.cycle_name is not None
        assert execution.status is not None
        assert execution.environment is not None
        assert execution.environment_name is not None
        assert execution.executed_by is not None
        assert execution.executed_by_name is not None
        assert execution.executed_on is not None
        assert execution.actual_time is not None
        assert len(execution.steps) > 0
        assert isinstance(execution, Execution)

        # Test execution creation based on test case
        test_case = CaseFactory.create_with_steps(3)
        execution_with_test_case = ExecutionFactory.create(
            test_case=test_case, test_case_key=test_case.key
        )
        assert execution_with_test_case.test_case_key == test_case.key
        assert len(execution_with_test_case.steps) == 3

        # Test batch creation
        batch_size = 3
        executions = ExecutionFactory.create_batch(batch_size)
        assert len(executions) == batch_size
        assert all(e.id is not None for e in executions)
        assert len(set(e.id for e in executions)) == batch_size  # Unique IDs

    def test_zephyr_config_factory(self):
        """Test the ZephyrConfigFactory."""
        # Test creation with default values
        config = ZephyrConfigFactory.create()
        assert config.base_url.startswith(("http://", "https://"))
        assert config.api_token is not None
        assert config.project_key is not None
        assert isinstance(config, ZephyrConfig)

        # Test creation with custom values
        custom_config = ZephyrConfigFactory.create(
            base_url="https://custom-zephyrscale.example.com/v2",
            api_token="custom-token-123",
            project_key="CUSTOM",
        )
        assert custom_config.base_url == "https://custom-zephyrscale.example.com/v2"
        assert custom_config.api_token == "custom-token-123"
        assert custom_config.project_key == "CUSTOM"

    def test_paginated_response_factory(self):
        """Test the PaginatedResponseFactory."""
        # Test creation with default values
        response = PaginatedResponseFactory.create()
        assert isinstance(response.values, list)
        assert response.start_at is not None
        assert response.max_results is not None
        assert response.total_count is not None
        assert isinstance(response.is_last, bool)
        assert isinstance(response, PaginatedResponse)

        # Test creation with custom values
        values = [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}]
        custom_response = PaginatedResponseFactory.create(
            values=values, start_at=20, max_results=10, total_count=50, is_last=False
        )
        assert custom_response.values == values
        assert custom_response.start_at == 20
        assert custom_response.max_results == 10
        assert custom_response.total_count == 50
        assert custom_response.is_last is False

    def test_helper_methods(self):
        """Test helper methods in factories."""
        # Test CaseFactory.create_with_steps method if it exists
        if hasattr(CaseFactory, "create_with_steps"):
            case = CaseFactory.create_with_steps(5)
            assert len(case.steps) == 5
            assert all(isinstance(step, CaseStep) for step in case.steps)
            assert [step.index for step in case.steps] == [1, 2, 3, 4, 5]
