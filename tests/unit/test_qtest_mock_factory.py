"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from datetime import datetime, timedelta
from ztoq.qtest_mock_factory import (
    MockFactory,
    QTestAttachmentFactory,
    QTestAutomationSettingsFactory,
    QTestConfigFactory,
    QTestCustomFieldFactory,
    QTestDatasetFactory,
    QTestFieldFactory,
    QTestLinkFactory,
    QTestModuleFactory,
    QTestPaginatedResponseFactory,
    QTestParameterFactory,
    QTestParameterValueFactory,
    QTestProjectFactory,
    QTestPulseActionFactory,
    QTestPulseActionParameterFactory,
    QTestPulseConditionFactory,
    QTestPulseConstantFactory,
    QTestPulseRuleFactory,
    QTestPulseTriggerFactory,
    QTestReleaseFactory,
    QTestScenarioFeatureFactory,
    QTestStepFactory,
    QTestTestCaseFactory,
    QTestTestCycleFactory,
    QTestTestExecutionFactory,
    QTestTestLogFactory,
    QTestTestRunFactory,
)
from ztoq.qtest_models import (
    QTestTestRun,
    QTestTestLog,
    QTestPulseEventType,
    QTestPulseActionType,
    QTestParameter,
    QTestParameterValue,
    QTestField,
    QTestAutomationSettings,
    QTestCustomField,
    QTestLink,
    QTestPaginatedResponse,
    QTestConfig,
    QTestPulseCondition,
    QTestPulseActionParameter,
)

@pytest.mark.unit()
class TestQTestMockFactory:
    """Test suite for the qTest mock factory implementations."""

    def test_base_mock_factory(self):
        """Test the base MockFactory utility methods."""
        # Test random ID generation
        random_id = MockFactory.random_id()
        assert isinstance(random_id, int)
        assert 1000 <= random_id <= 9999

        # Test random string generation
        random_string = MockFactory.random_string()
        assert isinstance(random_string, str)
        assert len(random_string) == 8

        # Test random date generation
        random_date = MockFactory.random_date()
        assert random_date is not None

        # Test random boolean generation
        random_bool = MockFactory.random_bool()
        assert isinstance(random_bool, bool)

        # Test random list item selection
        items = [1, 2, 3, 4, 5]
        random_item = MockFactory.random_list_item(items)
        assert random_item in items

    def test_project_factory(self):
        """Test the QTestProjectFactory."""
        # Test single project creation
        project = QTestProjectFactory.create()
        assert project.id is not None
        assert project.name is not None
        assert project.description is not None
        assert project.start_date is not None
        assert project.end_date is not None
        assert project.status_name is not None

        # Test project creation with custom attributes
        custom_project = QTestProjectFactory.create(
            id=12345,
                name="Custom Project",
                description="Custom description",
                status_name="Inactive"
        )
        assert custom_project.id == 12345
        assert custom_project.name == "Custom Project"
        assert custom_project.description == "Custom description"
        assert custom_project.status_name == "Inactive"

        # Test batch creation
        batch_size = 5
        projects = QTestProjectFactory.create_batch(batch_size)
        assert len(projects) == batch_size
        assert all(p.id is not None for p in projects)
        assert len(set(p.id for p in projects)) == batch_size  # Unique IDs

    def test_module_factory(self):
        """Test the QTestModuleFactory."""
        # Test single module creation
        module = QTestModuleFactory.create()
        assert module.id is not None
        assert module.name is not None
        assert module.description is not None
        assert module.pid is not None
        assert module.path is not None

        # Test module creation with parent
        child_module = QTestModuleFactory.create(
            parent_id=module.id,
                parent_name=module.name
        )
        assert child_module.parent_id == module.id
        assert module.name in child_module.path

        # Test batch creation with hierarchy
        modules = QTestModuleFactory.create_batch(3, create_hierarchy=True)
        assert len(modules) == 4  # 3 + root module
        assert modules[0].parent_id is None  # Root module
        assert all(m.parent_id == modules[0].id for m in modules[1:])  # All children point to root

    def test_custom_field_factory(self):
        """Test the QTestCustomFieldFactory."""
        # Test creation with different field types
        string_field = QTestCustomFieldFactory.create(field_type="STRING")
        assert string_field.field_type == "STRING"
        assert isinstance(string_field.field_value, str)

        number_field = QTestCustomFieldFactory.create(field_type="NUMBER")
        assert number_field.field_type == "NUMBER"
        assert isinstance(number_field.field_value, int)

        checkbox_field = QTestCustomFieldFactory.create(field_type="CHECKBOX")
        assert checkbox_field.field_type == "CHECKBOX"
        assert isinstance(checkbox_field.field_value, bool)

        # Test batch creation
        fields = QTestCustomFieldFactory.create_batch(3)
        assert len(fields) == 3
        assert all(f.field_id is not None for f in fields)

    def test_step_factory(self):
        """Test the QTestStepFactory."""
        # Test single step creation
        step = QTestStepFactory.create()
        assert step.id is not None
        assert step.description is not None
        assert step.expected_result is not None
        assert step.order == 1

        # Test batch creation with sequential order
        steps = QTestStepFactory.create_batch(3)
        assert len(steps) == 3
        assert [s.order for s in steps] == [1, 2, 3]

    def test_test_case_factory(self):
        """Test the QTestTestCaseFactory."""
        # Create custom fields for test
        properties = [
            QTestCustomFieldFactory.create(),
            QTestCustomFieldFactory.create()
        ]

        # Test single test case creation
        test_case = QTestTestCaseFactory.create(properties=properties)
        assert test_case.id is not None
        assert test_case.name is not None
        assert test_case.description is not None
        assert test_case.precondition is not None
        assert len(test_case.test_steps) == 3
        assert len(test_case.properties) == 2
        assert test_case.module_id is not None
        assert test_case.create_date is not None
        assert test_case.last_modified_date is not None
        assert test_case.project_id is not None

        # Test batch creation with properties
        test_cases = QTestTestCaseFactory.create_batch(3, properties=properties)
        assert len(test_cases) == 3
        assert all(tc.id is not None for tc in test_cases)
        assert len(set(tc.id for tc in test_cases)) == 3  # Unique IDs

    def test_release_factory(self):
        """Test the QTestReleaseFactory."""
        # Test single release creation
        release = QTestReleaseFactory.create()
        assert release.id is not None
        assert release.name is not None
        assert release.description is not None
        assert release.pid is not None
        assert release.start_date is not None
        assert release.end_date is not None
        assert release.project_id is not None

        # Test batch creation
        releases = QTestReleaseFactory.create_batch(3)
        assert len(releases) == 3
        assert all(r.id is not None for r in releases)

    def test_test_cycle_factory(self):
        """Test the QTestTestCycleFactory."""
        # Test single test cycle creation
        test_cycle = QTestTestCycleFactory.create()
        assert test_cycle.id is not None
        assert test_cycle.name is not None
        assert test_cycle.description is not None
        assert test_cycle.pid is not None
        assert test_cycle.release_id is not None
        assert test_cycle.project_id is not None
        assert len(test_cycle.properties) == 2
        assert test_cycle.start_date is not None
        assert test_cycle.end_date is not None

        # Test batch creation
        test_cycles = QTestTestCycleFactory.create_batch(3)
        assert len(test_cycles) == 3
        assert all(tc.id is not None for tc in test_cycles)

    def test_test_run_factory(self):
        """Test the QTestTestRunFactory."""
        # Create properties for test
        properties = [
            QTestCustomFieldFactory.create(),
            QTestCustomFieldFactory.create()
        ]

        # Test single test run creation
        test_run = QTestTestRunFactory.create(properties=properties)
        assert test_run.id is not None
        assert test_run.name is not None
        assert test_run.description is not None
        assert test_run.pid is not None
        assert test_run.test_case_id is not None
        assert test_run.test_cycle_id is not None
        assert test_run.project_id is not None
        assert len(test_run.properties) == 2
        assert test_run.status in QTestTestRun.VALID_STATUSES

        # Test creation with test case
        test_case = QTestTestCaseFactory.create()
        test_run_with_case = QTestTestRunFactory.create(test_case=test_case)
        assert test_run_with_case.test_case_id == test_case.id
        assert test_case.name in test_run_with_case.name

        # Test batch creation
        test_runs = QTestTestRunFactory.create_batch(3, properties=properties)
        assert len(test_runs) == 3
        assert all(tr.id is not None for tr in test_runs)

    def test_test_log_factory(self):
        """Test the QTestTestLogFactory."""
        # Create properties for test
        properties = [QTestCustomFieldFactory.create()]

        # Test single test log creation
        test_log = QTestTestLogFactory.create(properties=properties)
        assert test_log.id is not None
        assert test_log.status in QTestTestLog.VALID_STATUSES
        assert test_log.execution_date is not None
        assert test_log.note is not None
        assert len(test_log.properties) == 1
        assert test_log.test_run_id is not None

        # Test batch creation
        test_logs = QTestTestLogFactory.create_batch(3, properties=properties)
        assert len(test_logs) == 3
        assert all(tl.id is not None for tl in test_logs)

    def test_attachment_factory(self):
        """Test the QTestAttachmentFactory."""
        # Test single attachment creation
        attachment = QTestAttachmentFactory.create()
        assert attachment["id"] is not None
        assert attachment["name"] is not None
        assert attachment["contentType"] in QTestAttachmentFactory.CONTENT_TYPES
        assert attachment["size"] is not None
        assert attachment["createdDate"] is not None
        assert attachment["webUrl"] is not None

        # Test batch creation
        attachments = QTestAttachmentFactory.create_batch(3)
        assert len(attachments) == 3
        assert all(a["id"] is not None for a in attachments)

    def test_parameter_factory(self):
        """Test the QTestParameterFactory."""
        # Create parameter values for test
        param_id = 12345
        values = QTestParameterValueFactory.create_batch(3, parameter_id=param_id)

        # Test single parameter creation with provided values
        parameter = QTestParameterFactory.create(id=param_id, values=values)
        assert parameter.id == param_id
        assert parameter.name is not None
        assert parameter.description is not None
        assert parameter.project_id is not None
        assert parameter.status == "Active"
        assert len(parameter.values) == 3

        # Check that all parameter values have correct parameter_id
        for value in parameter.values:
            assert value.parameter_id == param_id
            assert isinstance(value.value, str)

        # Test parameter value factory
        param_value = QTestParameterValueFactory.create(value="Test Value")
        assert param_value.value == "Test Value"
        assert param_value.id is not None
        assert param_value.parameter_id is not None

        # Test batch creation
        parameters = QTestParameterFactory.create_batch(3)
        assert len(parameters) == 3
        assert all(p.id is not None for p in parameters)
        assert all(len(p.values) >= 2 for p in parameters)

    def test_dataset_factory(self):
        """Test the QTestDatasetFactory."""
        # Test single dataset creation
        dataset = QTestDatasetFactory.create()
        assert dataset.id is not None
        assert dataset.name is not None
        assert dataset.description is not None
        assert dataset.project_id is not None
        assert dataset.status == "Active"
        assert len(dataset.rows) >= 2
        assert all(r.dataset_id == dataset.id for r in dataset.rows)

        # Test custom parameter names
        custom_params = ["username", "password", "expected"]
        dataset_with_params = QTestDatasetFactory.create(parameter_names=custom_params)
        assert len(dataset_with_params.rows) >= 2
        assert dataset_with_params.parameter_names == custom_params
        for row in dataset_with_params.rows:
            for param in custom_params:
                assert param in row.values

        # Test batch creation
        datasets = QTestDatasetFactory.create_batch(3)
        assert len(datasets) == 3
        assert all(d.id is not None for d in datasets)

    def test_pulse_trigger_factory(self):
        """Test the QTestPulseTriggerFactory."""
        from ztoq.qtest_models import QTestPulseEventType

        # Test single trigger creation
        trigger = QTestPulseTriggerFactory.create()
        assert trigger.id is not None
        assert trigger.name is not None
        assert trigger.event_type in list(QTestPulseEventType)
        assert trigger.project_id is not None
        assert isinstance(trigger.conditions, list)
        assert trigger.created_by is not None
        assert trigger.created_date is not None

        # Test with specific event type
        specific_trigger = QTestPulseTriggerFactory.create(event_type=QTestPulseEventType.TEST_CASE_CREATED)
        assert specific_trigger.event_type == QTestPulseEventType.TEST_CASE_CREATED

        # Test batch creation
        triggers = QTestPulseTriggerFactory.create_batch(3)
        assert len(triggers) == 3
        assert all(t.id is not None for t in triggers)

    def test_pulse_action_factory(self):
        """Test the QTestPulseActionFactory."""
        # Email action parameters (comply with SEND_MAIL action type requirements)
        email_parameters = [
            QTestPulseActionParameterFactory.create(name="recipients", value="test@example.com"),
            QTestPulseActionParameterFactory.create(name="subject", value="Test notification"),
            QTestPulseActionParameterFactory.create(name="body", value="Test message body")
        ]

        # Test single action creation with email action
        action = QTestPulseActionFactory.create(
            action_type=QTestPulseActionType.SEND_MAIL,
            parameters=email_parameters
        )
        assert action.id is not None
        assert action.name is not None
        assert action.action_type == QTestPulseActionType.SEND_MAIL
        assert action.project_id is not None
        assert isinstance(action.parameters, list)
        assert len(action.parameters) == 3
        assert action.created_by is not None
        assert action.created_date is not None

        # Webhook parameters
        webhook_parameters = [
            QTestPulseActionParameterFactory.create(name="url", value="https://example.com/webhook"),
            QTestPulseActionParameterFactory.create(name="method", value="POST")
        ]

        # Test webhook action
        webhook_action = QTestPulseActionFactory.create(
            action_type=QTestPulseActionType.WEBHOOK,
            parameters=webhook_parameters
        )
        assert webhook_action.action_type == QTestPulseActionType.WEBHOOK
        assert len(webhook_action.parameters) == 2
        assert any(p.name == "url" for p in webhook_action.parameters)
        assert any(p.name == "method" for p in webhook_action.parameters)

        # Test the create method without specifying parameters (should create valid defaults)
        default_action = QTestPulseActionFactory.create()
        assert default_action.id is not None
        assert default_action.action_type is not None
        assert isinstance(default_action.parameters, list)

        # Single test batch creation with hardcoded parameters
        action_type = QTestPulseActionType.SEND_MAIL
        actions = [
            QTestPulseActionFactory.create(
                action_type=action_type,
                parameters=email_parameters
            )
            for _ in range(3)
        ]
        assert len(actions) == 3
        assert all(a.id is not None for a in actions)
        assert all(a.action_type == action_type for a in actions)

    def test_pulse_constant_factory(self):
        """Test the QTestPulseConstantFactory."""
        # Test single constant creation
        constant = QTestPulseConstantFactory.create()
        assert constant.id is not None
        assert constant.name is not None
        assert constant.name.isupper()  # Constants should be uppercase
        assert constant.value is not None
        assert constant.description is not None
        assert constant.project_id is not None
        assert constant.created_by is not None
        assert constant.created_date is not None

        # Test batch creation
        constants = QTestPulseConstantFactory.create_batch(3)
        assert len(constants) == 3
        assert all(c.id is not None for c in constants)

    def test_pulse_rule_factory(self):
        """Test the QTestPulseRuleFactory."""
        # Create trigger and action for test
        from ztoq.qtest_models import QTestPulseEventType, QTestPulseActionType

        trigger = QTestPulseTriggerFactory.create(event_type=QTestPulseEventType.TEST_CASE_CREATED)
        action = QTestPulseActionFactory.create(action_type=QTestPulseActionType.CREATE_DEFECT)

        # Test single rule creation with existing trigger and action
        rule = QTestPulseRuleFactory.create(trigger=trigger, action=action)
        assert rule.id is not None
        assert rule.name is not None
        assert rule.description is not None
        assert rule.project_id is not None
        assert rule.enabled is True
        assert rule.trigger_id == trigger.id
        assert rule.action_id == action.id
        assert rule.created_by is not None
        assert rule.created_date is not None

        # Test batch creation with trigger_id and action_id
        project_id = QTestProjectFactory.create().id
        rules = QTestPulseRuleFactory.create_batch(3,
                                                trigger_id=trigger.id,
                                                action_id=action.id,
                                                project_id=project_id)
        assert len(rules) == 3
        assert all(r.id is not None for r in rules)
        assert all(r.trigger_id == trigger.id for r in rules)
        assert all(r.action_id == action.id for r in rules)
        assert all(r.project_id == project_id for r in rules)

    def test_scenario_feature_factory(self):
        """Test the QTestScenarioFeatureFactory."""
        # Test single feature creation
        feature = QTestScenarioFeatureFactory.create()
        assert feature.id is not None
        assert feature.name is not None
        assert feature.description is not None
        assert feature.project_id is not None
        assert feature.content is not None
        assert "Feature:" in feature.content
        assert "Scenario:" in feature.content
        assert "Given" in feature.content
        assert "When" in feature.content
        assert "Then" in feature.content

        # Test batch creation
        features = QTestScenarioFeatureFactory.create_batch(3)
        assert len(features) == 3
        assert all(f.id is not None for f in features)
        assert len(set(f.id for f in features)) == 3  # Unique IDs

    def test_config_factory(self):
        """Test the QTestConfigFactory."""
        # Test creation with default values
        config = QTestConfigFactory.create()
        assert config.base_url.startswith(("http://", "https://"))
        assert config.username is not None
        assert config.password is not None
        assert config.project_id is not None

        # Test creation with custom values
        custom_config = QTestConfigFactory.create(
            base_url="https://custom-qtest.example.com",
            username="custom_user",
            password="custom_pass",
            project_id=12345
        )
        assert custom_config.base_url == "https://custom-qtest.example.com"
        assert custom_config.username == "custom_user"
        assert custom_config.password == "custom_pass"
        assert custom_config.project_id == 12345

    def test_paginated_response_factory(self):
        """Test the QTestPaginatedResponseFactory."""
        # Test creation with default values
        response = QTestPaginatedResponseFactory.create()
        assert isinstance(response.items, list)
        assert response.page is not None
        assert response.page_size is not None
        assert response.total is not None
        assert isinstance(response.is_last, bool)

        # Test creation with custom items and pagination
        custom_items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        custom_response = QTestPaginatedResponseFactory.create(
            items=custom_items,
            page=2,
            page_size=10,
            total=25,
            is_last=False
        )
        assert custom_response.items == custom_items
        assert custom_response.page == 2
        assert custom_response.page_size == 10
        assert custom_response.total == 25
        assert custom_response.is_last is False

    def test_link_factory(self):
        """Test the QTestLinkFactory."""
        # Test single link creation
        link = QTestLinkFactory.create()
        assert link.id is not None
        assert link.name is not None
        assert link.url.startswith(("http://", "https://"))
        assert link.icon_url is not None
        assert link.target is not None

        # Test custom link creation
        custom_link = QTestLinkFactory.create(
            id=12345,
            name="Custom Link",
            url="https://example.com/custom",
            icon_url="https://example.com/icons/custom.png",
            target="_self"
        )
        assert custom_link.id == 12345
        assert custom_link.name == "Custom Link"
        assert custom_link.url == "https://example.com/custom"
        assert custom_link.icon_url == "https://example.com/icons/custom.png"
        assert custom_link.target == "_self"

        # Test batch creation
        links = QTestLinkFactory.create_batch(3)
        assert len(links) == 3
        assert all(l.id is not None for l in links)
        assert len(set(l.id for l in links)) == 3  # Unique IDs

    def test_field_factory(self):
        """Test the QTestFieldFactory."""
        # Test single field creation
        field = QTestFieldFactory.create()
        assert field.id is not None
        assert field.name is not None
        assert field.label is not None
        assert field.field_type in QTestFieldFactory.create().VALID_FIELD_TYPES
        assert field.entity_type in QTestFieldFactory.create().VALID_ENTITY_TYPES

        # Test custom field creation
        custom_field = QTestFieldFactory.create(
            id=12345,
            name="custom_field",
            label="Custom Field",
            field_type="STRING",
            entity_type="TEST_CASE",
            allowed_values=["value1", "value2"],
            required=True
        )
        assert custom_field.id == 12345
        assert custom_field.name == "custom_field"
        assert custom_field.label == "Custom Field"
        assert custom_field.field_type == "STRING"
        assert custom_field.entity_type == "TEST_CASE"
        assert custom_field.allowed_values == ["value1", "value2"]
        assert custom_field.required is True

        # Test batch creation
        fields = QTestFieldFactory.create_batch(3)
        assert len(fields) == 3
        assert all(f.id is not None for f in fields)

    def test_automation_settings_factory(self):
        """Test the QTestAutomationSettingsFactory."""
        # Test creation with default values
        settings = QTestAutomationSettingsFactory.create()
        assert settings.automation_id is not None
        assert settings.framework_id is not None
        assert settings.framework_name is not None
        assert isinstance(settings.parameters, dict)
        assert isinstance(settings.is_parameterized, bool)
        assert settings.external_id is not None

        # Test creation with custom values
        custom_settings = QTestAutomationSettingsFactory.create(
            automation_id="custom-auto-123",
            framework_id=12345,
            framework_name="Custom Framework",
            parameters={"key1": "value1", "key2": "value2"},
            is_parameterized=True,
            external_id="EXT-123"
        )
        assert custom_settings.automation_id == "custom-auto-123"
        assert custom_settings.framework_id == 12345
        assert custom_settings.framework_name == "Custom Framework"
        assert custom_settings.parameters == {"key1": "value1", "key2": "value2"}
        assert custom_settings.is_parameterized is True
        assert custom_settings.external_id == "EXT-123"

    def test_test_execution_factory(self):
        """Test the QTestTestExecutionFactory."""
        # Test single test execution creation
        execution = QTestTestExecutionFactory.create()
        assert execution.id is not None
        assert execution.test_run_id is not None
        assert execution.status in QTestTestExecutionFactory.create().VALID_STATUSES
        assert execution.execution_date is not None
        assert execution.note is not None
        assert isinstance(execution.test_step_logs, list)

        # Test custom test execution creation
        test_step_logs = [
            {"stepId": 1, "status": "Passed", "actualResult": "Test passed successfully"},
            {"stepId": 2, "status": "Failed", "actualResult": "Test failed unexpectedly"}
        ]
        custom_execution = QTestTestExecutionFactory.create(
            id=12345,
            test_run_id=67890,
            status="Failed",
            executed_by=9876,
            test_step_logs=test_step_logs,
            build="2.0.123",
            duration=5000
        )
        assert custom_execution.id == 12345
        assert custom_execution.test_run_id == 67890
        assert custom_execution.status == "Failed"
        assert custom_execution.executed_by == 9876
        assert custom_execution.test_step_logs == test_step_logs
        assert custom_execution.build == "2.0.123"
        assert custom_execution.duration == 5000

        # Test batch creation
        executions = QTestTestExecutionFactory.create_batch(3)
        assert len(executions) == 3
        assert all(e.id is not None for e in executions)
        assert all(e.test_run_id is not None for e in executions)

    def test_pulse_condition_factory(self):
        """Test the QTestPulseConditionFactory."""
        # Test single condition creation
        condition = QTestPulseConditionFactory.create()
        assert condition.field is not None
        assert condition.operator in QTestPulseConditionFactory.create().VALID_OPERATORS
        assert hasattr(condition, "value")  # Value could be None for some operators

        # Test custom condition creation
        custom_condition = QTestPulseConditionFactory.create(
            field="status",
            operator="equals",
            value="Failed",
            value_type="string"
        )
        assert custom_condition.field == "status"
        assert custom_condition.operator == "equals"
        assert custom_condition.value == "Failed"
        assert custom_condition.value_type == "string"

        # Test different operator types
        equals_condition = QTestPulseConditionFactory.create(operator="equals")
        assert equals_condition.value is not None

        greater_condition = QTestPulseConditionFactory.create(operator="greater_than")
        assert isinstance(greater_condition.value, int)

        # Test batch creation
        conditions = QTestPulseConditionFactory.create_batch(3)
        assert len(conditions) == 3
        assert all(c.field is not None for c in conditions)
        assert all(c.operator in QTestPulseConditionFactory.create().VALID_OPERATORS for c in conditions)

    def test_pulse_action_parameter_factory(self):
        """Test the QTestPulseActionParameterFactory."""
        # Test single parameter creation
        parameter = QTestPulseActionParameterFactory.create()
        assert parameter.name is not None
        assert parameter.value is not None
        assert parameter.value_type in QTestPulseActionParameterFactory.create().VALID_VALUE_TYPES

        # Test creation with different value types
        string_param = QTestPulseActionParameterFactory.create(value_type="string")
        assert isinstance(string_param.value, str)

        number_param = QTestPulseActionParameterFactory.create(value_type="number")
        assert isinstance(number_param.value, int)

        bool_param = QTestPulseActionParameterFactory.create(value_type="boolean")
        assert isinstance(bool_param.value, bool)

        array_param = QTestPulseActionParameterFactory.create(value_type="array")
        assert isinstance(array_param.value, list)

        object_param = QTestPulseActionParameterFactory.create(value_type="object")
        assert isinstance(object_param.value, dict)

        # Test custom parameter creation
        custom_param = QTestPulseActionParameterFactory.create(
            name="custom_param",
            value={"key": "value"},
            value_type="object"
        )
        assert custom_param.name == "custom_param"
        assert custom_param.value == {"key": "value"}
        assert custom_param.value_type == "object"

        # Test parameter handling for webhook action
        webhook_param = QTestPulseActionParameterFactory.create(
            name="url",
            value="https://example.com/webhook",
            value_type="string"
        )
        assert webhook_param.name == "url"
        assert webhook_param.value == "https://example.com/webhook"

        # Test handling special characters in string values
        special_param = QTestPulseActionParameterFactory.create(
            name="template",
            value="{{testCase.name}} - {{testRun.status}}",
            value_type="string"
        )
        assert "{{testCase.name}}" in special_param.value
        assert "{{testRun.status}}" in special_param.value

        # Test batch creation with consistent value types
        parameters = QTestPulseActionParameterFactory.create_batch(3, value_type="number")
        assert len(parameters) == 3
        assert all(p.name is not None for p in parameters)
        assert all(p.value is not None for p in parameters)
        assert all(isinstance(p.value, int) for p in parameters)
        assert all(p.value_type == "number" for p in parameters)

    def test_edge_case_validations(self):
        """Test edge cases and validation handling in the factories."""
        # Test project factory with same start and end date
        start_date = datetime.now()
        project = QTestProjectFactory.create(start_date=start_date, end_date=start_date)
        assert project.start_date == project.end_date

        # Test project with end date before start date should fail validation
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            QTestProjectFactory.create(
                start_date=datetime.now() + timedelta(days=10),
                end_date=datetime.now()
            )

        # Test test case factory with multiple steps but manual order
        steps = [
            QTestStepFactory.create(order=1, description="First step"),
            QTestStepFactory.create(order=2, description="Second step"),
            QTestStepFactory.create(order=3, description="Third step")
        ]
        test_case = QTestTestCaseFactory.create(test_steps=steps)
        assert len(test_case.test_steps) == 3
        assert [s.order for s in test_case.test_steps] == [1, 2, 3]

        # Test test case with non-sequential steps should fail validation
        with pytest.raises(ValueError, match="Test step orders must be sequential and increasing"):
            non_sequential_steps = [
                QTestStepFactory.create(order=1),
                QTestStepFactory.create(order=3),  # Skip order 2
                QTestStepFactory.create(order=2)   # Out of order
            ]
            QTestTestCaseFactory.create(test_steps=non_sequential_steps)

    def test_model_validation_compliance(self):
        """Test that factories comply with model validations."""
        # Test that QTestField factory creates entities with valid field types
        field = QTestFieldFactory.create()
        assert field.field_type in QTestField.VALID_FIELD_TYPES
        assert field.entity_type in QTestField.VALID_ENTITY_TYPES

        # Test that QTestCustomField factory creates properly typed values
        string_field = QTestCustomFieldFactory.create(field_type="STRING")
        assert isinstance(string_field.field_value, str)

        number_field = QTestCustomFieldFactory.create(field_type="NUMBER")
        assert isinstance(number_field.field_value, (int, float))

        bool_field = QTestCustomFieldFactory.create(field_type="CHECKBOX")
        assert isinstance(bool_field.field_value, bool)

        # Test that QTestPulseCondition factory creates valid operators
        condition = QTestPulseConditionFactory.create()
        assert condition.operator in QTestPulseCondition.VALID_OPERATORS

        # Test equals condition with string value
        equals_condition = QTestPulseConditionFactory.create(
            operator="equals",
            field="status",
            value="Passed"
        )
        assert equals_condition.operator == "equals"
        assert equals_condition.field == "status"
        assert equals_condition.value == "Passed"

        # Test numeric comparison with correct value type
        number_condition = QTestPulseConditionFactory.create(
            operator="greater_than",
            field="priority",
            value=2,
            value_type="number"
        )
        assert number_condition.operator == "greater_than"
        assert isinstance(number_condition.value, int)
        assert number_condition.value_type == "number"

    def test_complex_factory_relationships(self):
        """Test factories that create complex object relationships."""
        # Test creating test case with full hierarchy
        project = QTestProjectFactory.create()
        module = QTestModuleFactory.create(project_id=project.id)
        steps = QTestStepFactory.create_batch(3)
        properties = QTestCustomFieldFactory.create_batch(2)
        automation = QTestAutomationSettingsFactory.create()

        test_case = QTestTestCaseFactory.create(
            project_id=project.id,
            module_id=module.id,
            test_steps=steps,
            properties=properties,
            automation=automation
        )

        assert test_case.project_id == project.id
        assert test_case.module_id == module.id
        assert len(test_case.test_steps) == 3
        assert len(test_case.properties) == 2
        assert test_case.automation is not None

        # Test creating pulse rule with related objects
        trigger = QTestPulseTriggerFactory.create(project_id=project.id)
        action = QTestPulseActionFactory.create(project_id=project.id)

        rule = QTestPulseRuleFactory.create(
            project_id=project.id,
            trigger=trigger,
            action=action
        )

        assert rule.project_id == project.id
        assert rule.trigger_id == trigger.id
        assert rule.action_id == action.id

        # Test cycle with test runs and test logs
        test_cycle = QTestTestCycleFactory.create(project_id=project.id)
        test_runs = []

        # Create test runs in the cycle
        for i in range(3):
            run = QTestTestRunFactory.create(
                test_cycle_id=test_cycle.id,
                test_case_id=test_case.id,
                project_id=project.id
            )
            test_runs.append(run)

            # Add test log to the run
            log = QTestTestLogFactory.create(
                test_run_id=run.id,
                status=QTestTestLog.VALID_STATUSES[i % len(QTestTestLog.VALID_STATUSES)]
            )
            assert log.test_run_id == run.id

        assert len(test_runs) == 3
        assert all(r.test_cycle_id == test_cycle.id for r in test_runs)
        assert all(r.test_case_id == test_case.id for r in test_runs)

    def test_pagination_and_config_factories(self):
        """Test factories for pagination responses and configuration."""
        # Test pagination with custom items
        custom_items = [{"id": i, "name": f"Item {i}"} for i in range(5)]
        paginated = QTestPaginatedResponseFactory.create(
            items=custom_items,
            page=2,
            page_size=5,
            total=20,
            is_last=False
        )

        assert isinstance(paginated, QTestPaginatedResponse)
        assert paginated.items == custom_items
        assert paginated.page == 2
        assert paginated.page_size == 5
        assert paginated.total == 20
        assert paginated.is_last is False
        assert paginated.offset == 5  # (page-1) * page_size

        # Test pagination for last page
        last_page = QTestPaginatedResponseFactory.create(
            page=4,
            page_size=5,
            total=20,
            is_last=True
        )
        assert last_page.is_last is True
        assert last_page.offset == 15

        # Test config with custom values
        config = QTestConfigFactory.create(
            base_url="https://custom.qtest.com",
            username="test_user",
            password="test_password",
            project_id=12345
        )

        assert isinstance(config, QTestConfig)
        assert config.base_url == "https://custom.qtest.com"
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.project_id == 12345

        # Test default config values
        default_config = QTestConfigFactory.create()
        assert default_config.base_url.startswith(("http://", "https://"))
        assert default_config.username is not None
        assert default_config.password is not None
        assert default_config.project_id > 0

    def test_test_execution_factory(self):
        """Test the QTestTestExecutionFactory in depth."""
        # Test basic execution creation
        execution = QTestTestExecutionFactory.create()
        assert execution.test_run_id is not None
        assert execution.status in execution.VALID_STATUSES
        assert execution.execution_date is not None

        # Test custom execution with all fields
        custom_execution = QTestTestExecutionFactory.create(
            id=12345,
            test_run_id=6789,
            status="Passed",
            execution_date=datetime.now(),
            executed_by=101,
            note="Test execution completed successfully",
            build="1.2.345",
            build_url="https://jenkins.example.com/build/345",
            duration=12500  # 12.5 seconds
        )

        assert custom_execution.id == 12345
        assert custom_execution.test_run_id == 6789
        assert custom_execution.status == "Passed"
        assert custom_execution.executed_by == 101
        assert custom_execution.note == "Test execution completed successfully"
        assert custom_execution.build == "1.2.345"
        assert custom_execution.build_url == "https://jenkins.example.com/build/345"
        assert custom_execution.duration == 12500

        # Test with test step logs
        step_logs = [
            {"stepId": 1, "status": "Passed", "actualResult": "First step passed"},
            {"stepId": 2, "status": "Failed", "actualResult": "Second step failed", "executionNotes": "Exception occurred"}
        ]

        step_execution = QTestTestExecutionFactory.create(
            test_step_logs=step_logs,
            status="Failed"  # Overall status is failed because a step failed
        )

        assert step_execution.test_step_logs == step_logs
        assert step_execution.status == "Failed"
        assert len(step_execution.test_step_logs) == 2

        # Test batch creation with consistent status
        executions = QTestTestExecutionFactory.create_batch(5, status="Passed")
        assert len(executions) == 5
        assert all(e.status == "Passed" for e in executions)

    def test_attachment_factory(self):
        """Test the attachment factory."""
        # Test creation of attachment dictionaries (not models)
        png_attachment = QTestAttachmentFactory.create(
            contentType="image/png",
            name="screenshot.png"
        )
        assert png_attachment["contentType"] == "image/png"
        assert png_attachment["name"] == "screenshot.png"

        pdf_attachment = QTestAttachmentFactory.create(
            contentType="application/pdf",
            name="report.pdf"
        )
        assert pdf_attachment["contentType"] == "application/pdf"
        assert pdf_attachment["name"] == "report.pdf"

        # Testing actual attachment usage
        # Note: QTestAttachment is for the API model, not used directly in these tests
        # The factories return attachment dictionaries for API compatibility

        # Create batch of attachments
        attachments = QTestAttachmentFactory.create_batch(3)
        assert len(attachments) == 3
        assert all(isinstance(a, dict) for a in attachments)
        assert all("contentType" in a for a in attachments)
        assert all("name" in a for a in attachments)

        # These attachments can be used in test cases, steps, and logs
        test_case = QTestTestCaseFactory.create(attachments=attachments)
        assert len(test_case.attachments) == 3

    def test_dataset_and_parameters(self):
        """Test dataset and parameter factories in depth."""
        # Create parameter with values
        param_id = MockFactory.random_id()
        param_values = QTestParameterValueFactory.create_batch(3, parameter_id=param_id)
        parameter = QTestParameterFactory.create(id=param_id, values=param_values)
        assert len(parameter.values) == 3
        assert all(v.parameter_id == param_id for v in parameter.values)

        # Create dataset with specific parameter names
        param_names = ["browser", "platform", "version"]
        dataset = QTestDatasetFactory.create(parameter_names=param_names)
        assert dataset.parameter_names == param_names
        assert len(dataset.rows) >= 2

        # Test each row has values for all parameters
        for row in dataset.rows:
            assert row.dataset_id == dataset.id  # All rows have correct dataset ID
            for param in param_names:
                assert param in row.values
                assert row.values[param] is not None

    def test_factory_customization_patterns(self):
        """Test patterns for customizing factory output."""
        # Test creating related entities with consistent project ID
        project_id = 12345

        # Create multiple entities with the same project ID
        entities = [
            QTestProjectFactory.create(id=project_id),
            QTestModuleFactory.create(project_id=project_id),
            QTestTestCaseFactory.create(project_id=project_id),
            QTestTestCycleFactory.create(project_id=project_id),
            QTestReleaseFactory.create(project_id=project_id),
            QTestPulseRuleFactory.create(project_id=project_id)
        ]

        # All entities should have the same project ID
        assert all(getattr(e, "project_id", e.id) == project_id for e in entities)

        # Test creating a complete test suite structure
        module = QTestModuleFactory.create(name="Test Module")

        # Create 5 test cases in the module with 3 steps each
        test_cases = []
        for i in range(5):
            steps = QTestStepFactory.create_batch(3)
            test_case = QTestTestCaseFactory.create(
                name=f"Test Case {i+1}",
                module_id=module.id,
                test_steps=steps
            )
            test_cases.append(test_case)

        # Create a test cycle with test runs for each test case
        test_cycle = QTestTestCycleFactory.create(name="Regression Cycle")
        test_runs = []

        for test_case in test_cases:
            run = QTestTestRunFactory.create(
                test_case_id=test_case.id,
                test_cycle_id=test_cycle.id,
                name=f"Run for {test_case.name}"
            )
            test_runs.append(run)

        assert len(test_runs) == 5
        assert all(r.test_cycle_id == test_cycle.id for r in test_runs)

        # Map test case IDs to test run IDs
        test_case_to_run = {run.test_case_id: run.id for run in test_runs}

        # Verify we have a run for each test case
        for test_case in test_cases:
            assert test_case.id in test_case_to_run

    def test_advanced_pulse_scenarios(self):
        """Test advanced qTest Pulse factory scenarios."""
        # Test creating scheduled trigger
        scheduled_trigger = QTestPulseTriggerFactory.create(
            event_type=QTestPulseEventType.SCHEDULED,
            conditions=[
                QTestPulseConditionFactory.create(
                    field="schedule",
                    operator="equals",
                    value="0 0 * * *"  # Daily at midnight
                )
            ]
        )

        assert scheduled_trigger.event_type == QTestPulseEventType.SCHEDULED
        assert len(scheduled_trigger.conditions) == 1
        assert scheduled_trigger.conditions[0].field == "schedule"

        # Test creating webhook action
        webhook_parameters = [
            QTestPulseActionParameterFactory.create(name="url", value="https://example.com/webhook"),
            QTestPulseActionParameterFactory.create(name="method", value="POST"),
            QTestPulseActionParameterFactory.create(
                name="headers",
                value={"Content-Type": "application/json", "Authorization": "Bearer token123"},
                value_type="object"
            ),
            QTestPulseActionParameterFactory.create(
                name="body",
                value={
                    "event": "{{event.type}}",
                    "testCase": {
                        "id": "{{testCase.id}}",
                        "name": "{{testCase.name}}"
                    }
                },
                value_type="object"
            )
        ]

        webhook_action = QTestPulseActionFactory.create(
            action_type=QTestPulseActionType.WEBHOOK,
            parameters=webhook_parameters
        )

        assert webhook_action.action_type == QTestPulseActionType.WEBHOOK
        assert len(webhook_action.parameters) == 4
        assert any(p.name == "url" for p in webhook_action.parameters)
        assert any(p.name == "method" for p in webhook_action.parameters)
        assert any(p.name == "headers" for p in webhook_action.parameters)
        assert any(p.name == "body" for p in webhook_action.parameters)

        # Test creating a complex rule for test failure notification
        test_failure_trigger = QTestPulseTriggerFactory.create(
            name="Test Run Failed Trigger",
            event_type=QTestPulseEventType.TEST_LOG_CREATED,
            conditions=[
                QTestPulseConditionFactory.create(
                    field="status",
                    operator="equals",
                    value="Failed"
                )
            ]
        )

        email_parameters = [
            QTestPulseActionParameterFactory.create(name="recipients", value="team@example.com"),
            QTestPulseActionParameterFactory.create(name="subject", value="Test Failed: {{testCase.name}}"),
            QTestPulseActionParameterFactory.create(
                name="body",
                value="""
                Test Case: {{testCase.name}}
                Status: {{testLog.status}}
                Executed By: {{testLog.executedBy.name}}
                Date: {{testLog.executionDate}}

                Please investigate this failure.
                """
            )
        ]

        email_action = QTestPulseActionFactory.create(
            name="Send Failure Email",
            action_type=QTestPulseActionType.SEND_MAIL,
            parameters=email_parameters
        )

        failure_rule = QTestPulseRuleFactory.create(
            name="Test Failure Notification",
            trigger=test_failure_trigger,
            action=email_action,
            enabled=True
        )

        assert failure_rule.name == "Test Failure Notification"
        assert failure_rule.trigger_id == test_failure_trigger.id
        assert failure_rule.action_id == email_action.id
        assert failure_rule.enabled is True

    def test_scenario_feature_integration(self):
        """Test scenario feature factory integration."""
        # Create a BDD feature
        feature = QTestScenarioFeatureFactory.create(
            name="Shopping Cart Feature"
        )

        assert feature.name == "Shopping Cart Feature"
        assert "Feature:" in feature.content
        assert "Scenario:" in feature.content

        # Test feature has consistent project ID
        project_id = MockFactory.random_id()
        feature_with_project = QTestScenarioFeatureFactory.create(
            project_id=project_id,
            name="Feature with Project ID"
        )
        assert feature_with_project.project_id == project_id

        # Basic verification of feature content structure
        assert "Feature:" in feature_with_project.content
        assert "Scenario:" in feature_with_project.content

        # Test that test cases can be created based on features
        # Create module for test cases
        module = QTestModuleFactory.create(project_id=project_id)

        # Create a test case linked to the feature
        test_case = QTestTestCaseFactory.create(
            name=f"Test for {feature_with_project.name}",
            module_id=module.id,
            project_id=project_id,
            description=f"Test case for feature: {feature_with_project.name}"
        )

        assert test_case.name.startswith("Test for")
        assert test_case.module_id == module.id
        assert test_case.project_id == project_id
