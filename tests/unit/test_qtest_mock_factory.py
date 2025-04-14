"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from ztoq.qtest_mock_factory import (
    MockFactory,
        QTestAttachmentFactory,
        QTestCustomFieldFactory,
        QTestDatasetFactory,
        QTestModuleFactory,
        QTestParameterFactory,
        QTestProjectFactory,
        QTestPulseActionFactory,
        QTestPulseConstantFactory,
        QTestPulseRuleFactory,
        QTestPulseTriggerFactory,
        QTestReleaseFactory,
        QTestScenarioFeatureFactory,
        QTestStepFactory,
        QTestTestCaseFactory,
        QTestTestCycleFactory,
        QTestTestLogFactory,
        QTestTestRunFactory,
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
        string_field = QTestCustomFieldFactory.create(type="STRING")
        assert string_field.field_type == "STRING"
        assert isinstance(string_field.field_value, str)

        number_field = QTestCustomFieldFactory.create(type="NUMBER")
        assert number_field.field_type == "NUMBER"
        assert isinstance(number_field.field_value, int)

        checkbox_field = QTestCustomFieldFactory.create(type="CHECKBOX")
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
        # Test single test case creation
        test_case = QTestTestCaseFactory.create()
        assert test_case.id is not None
        assert test_case.name is not None
        assert test_case.description is not None
        assert test_case.precondition is not None
        assert len(test_case.test_steps) == 3
        assert len(test_case.properties) == 2
        assert test_case.module_id is not None
        assert test_case.create_date is not None
        assert test_case.last_modified_date is not None

        # Test batch creation
        test_cases = QTestTestCaseFactory.create_batch(3)
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
        # Test single test run creation
        test_run = QTestTestRunFactory.create()
        assert test_run.id is not None
        assert test_run.name is not None
        assert test_run.description is not None
        assert test_run.pid is not None
        assert test_run.test_case_id is not None
        assert test_run.test_cycle_id is not None
        assert test_run.project_id is not None
        assert len(test_run.properties) == 2
        assert test_run.status == "NOT_EXECUTED"

        # Test creation with test case
        test_case = QTestTestCaseFactory.create()
        test_run_with_case = QTestTestRunFactory.create(test_case=test_case)
        assert test_run_with_case.test_case_id == test_case.id
        assert test_case.name in test_run_with_case.name

        # Test batch creation
        test_runs = QTestTestRunFactory.create_batch(3)
        assert len(test_runs) == 3
        assert all(tr.id is not None for tr in test_runs)

    def test_test_log_factory(self):
        """Test the QTestTestLogFactory."""
        # Test single test log creation
        test_log = QTestTestLogFactory.create()
        assert test_log.id is not None
        assert test_log.status in QTestTestLogFactory.TEST_STATUSES
        assert test_log.execution_date is not None
        assert test_log.note is not None
        assert len(test_log.properties) == 1

        # Test batch creation
        test_logs = QTestTestLogFactory.create_batch(3)
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
        # Test single parameter creation
        parameter = QTestParameterFactory.create()
        assert parameter.id is not None
        assert parameter.name is not None
        assert parameter.description is not None
        assert parameter.project_id is not None
        assert parameter.status == "ACTIVE"
        assert len(parameter.values) >= 2
        assert all(v.parameter_id == parameter.id for v in parameter.values)

        # Test batch creation
        parameters = QTestParameterFactory.create_batch(3)
        assert len(parameters) == 3
        assert all(p.id is not None for p in parameters)

    def test_dataset_factory(self):
        """Test the QTestDatasetFactory."""
        # Test single dataset creation
        dataset = QTestDatasetFactory.create()
        assert dataset.id is not None
        assert dataset.name is not None
        assert dataset.description is not None
        assert dataset.project_id is not None
        assert dataset.status == "ACTIVE"
        assert len(dataset.rows) >= 2
        assert all(r.dataset_id == dataset.id for r in dataset.rows)

        # Test custom columns
        custom_columns = ["username", "password", "expected"]
        dataset_with_columns = QTestDatasetFactory.create(columns=custom_columns)
        assert len(dataset_with_columns.rows) >= 2
        for row in dataset_with_columns.rows:
            for col in custom_columns:
                assert col in row.values

        # Test batch creation
        datasets = QTestDatasetFactory.create_batch(3)
        assert len(datasets) == 3
        assert all(d.id is not None for d in datasets)

    def test_pulse_trigger_factory(self):
        """Test the QTestPulseTriggerFactory."""
        # Test single trigger creation
        trigger = QTestPulseTriggerFactory.create()
        assert trigger.id is not None
        assert trigger.name is not None
        assert trigger.event_type in QTestPulseTriggerFactory.EVENT_TYPES
        assert trigger.project_id is not None
        assert isinstance(trigger.conditions, list)
        assert trigger.created_by is not None
        assert trigger.created_date is not None

        # Test batch creation
        triggers = QTestPulseTriggerFactory.create_batch(3)
        assert len(triggers) == 3
        assert all(t.id is not None for t in triggers)

    def test_pulse_action_factory(self):
        """Test the QTestPulseActionFactory."""
        # Test single action creation
        action = QTestPulseActionFactory.create()
        assert action.id is not None
        assert action.name is not None
        assert action.action_type in QTestPulseActionFactory.ACTION_TYPES
        assert action.project_id is not None
        assert isinstance(action.parameters, list)
        assert action.created_by is not None
        assert action.created_date is not None

        # Test specific action type
        defect_action = QTestPulseActionFactory.create(action_type="CREATE_DEFECT")
        assert defect_action.action_type == "CREATE_DEFECT"
        assert any(p.name == "issueType" for p in defect_action.parameters)

        # Test batch creation
        actions = QTestPulseActionFactory.create_batch(3)
        assert len(actions) == 3
        assert all(a.id is not None for a in actions)

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
        # Test single rule creation
        rule = QTestPulseRuleFactory.create()
        assert rule.id is not None
        assert rule.name is not None
        assert rule.description is not None
        assert rule.project_id is not None
        assert rule.enabled is True
        assert rule.trigger_id is not None
        assert rule.action_id is not None
        assert rule.created_by is not None
        assert rule.created_date is not None

        # Test batch creation
        rules = QTestPulseRuleFactory.create_batch(3)
        assert len(rules) == 3
        assert all(r.id is not None for r in rules)

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
