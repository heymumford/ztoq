"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from ztoq.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowConfig,
    WorkflowEvent,
    WorkflowPhase,
    WorkflowStatus,
)


class TestWorkflowOrchestrator(unittest.TestCase):
    """Test cases for the workflow orchestration system."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock database
        self.mock_db = MagicMock()

        # Create test configuration
        self.config = WorkflowConfig(
            project_key="TEST",
            db_type="sqlite",
            db_path=":memory:",
            batch_size=10,
            max_workers=2,
            validation_enabled=True,
        )

        # Patch the get_database_manager function
        self.db_manager_patcher = patch("ztoq.workflow_orchestrator.get_database_manager")
        self.mock_get_db_manager = self.db_manager_patcher.start()
        self.mock_get_db_manager.return_value = self.mock_db

        # Create orchestrator with mocked dependencies
        self.orchestrator = WorkflowOrchestrator(self.config)

        # Mock the migration state
        self.orchestrator.state = MagicMock()
        self.orchestrator.state.extraction_status = "not_started"
        self.orchestrator.state.transformation_status = "not_started"
        self.orchestrator.state.loading_status = "not_started"

        # Mock the migration
        self.orchestrator.migration = MagicMock()

    def tearDown(self):
        """Tear down test fixtures."""
        self.db_manager_patcher.stop()

    def test_workflow_event_creation(self):
        """Test creating a workflow event."""
        # Test with basic parameters
        event = WorkflowEvent(
            phase="extract",
            status="in_progress",
            message="Starting extraction",
        )

        self.assertEqual(event.phase, "extract")
        self.assertEqual(event.status, "in_progress")
        self.assertEqual(event.message, "Starting extraction")
        self.assertIsNone(event.entity_type)
        self.assertIsNone(event.entity_count)

        # Test with all parameters
        event = WorkflowEvent(
            phase="transform",
            status="completed",
            message="Transformation completed",
            entity_type="test_cases",
            entity_count=100,
            batch_number=2,
            total_batches=5,
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            metadata={"key": "value"},
        )

        self.assertEqual(event.phase, "transform")
        self.assertEqual(event.status, "completed")
        self.assertEqual(event.message, "Transformation completed")
        self.assertEqual(event.entity_type, "test_cases")
        self.assertEqual(event.entity_count, 100)
        self.assertEqual(event.batch_number, 2)
        self.assertEqual(event.total_batches, 5)
        self.assertEqual(event.timestamp, datetime(2025, 1, 1, 12, 0, 0))
        self.assertEqual(event.metadata, {"key": "value"})

        # Test as_dict method
        event_dict = event.as_dict()
        self.assertEqual(event_dict["phase"], "transform")
        self.assertEqual(event_dict["status"], "completed")
        self.assertEqual(event_dict["message"], "Transformation completed")
        self.assertEqual(event_dict["entity_type"], "test_cases")
        self.assertEqual(event_dict["entity_count"], 100)
        self.assertEqual(event_dict["timestamp"], "2025-01-01T12:00:00")

    def test_add_event(self):
        """Test adding a workflow event."""
        # Set up mock database
        self.mock_db.save_workflow_event = MagicMock()

        # Add an event
        event = self.orchestrator._add_event(
            phase="extract",
            status="in_progress",
            message="Starting extraction",
            entity_type="test_cases",
            entity_count=100,
        )

        # Check event was added to the events list
        self.assertEqual(len(self.orchestrator.events), 1)
        self.assertEqual(self.orchestrator.events[0], event)

        # Check event was saved to the database
        self.mock_db.save_workflow_event.assert_called_once()
        call_args = self.mock_db.save_workflow_event.call_args[0]
        self.assertEqual(call_args[0], "TEST")  # project_key
        self.assertEqual(call_args[1]["phase"], "extract")
        self.assertEqual(call_args[1]["status"], "in_progress")
        self.assertEqual(call_args[1]["message"], "Starting extraction")

    @patch("ztoq.workflow_orchestrator.asyncio.to_thread")
    async def test_run_extract_phase(self, mock_to_thread):
        """Test running the extract phase."""
        # Set up mocks
        mock_to_thread.return_value = None

        # Run the extract phase
        await self.orchestrator._run_extract_phase()

        # Check the extract_data method was called
        mock_to_thread.assert_called_once_with(self.orchestrator.migration.extract_data)

        # Check events were added
        self.assertEqual(len(self.orchestrator.events), 2)
        self.assertEqual(self.orchestrator.events[0].phase, "extract")
        self.assertEqual(self.orchestrator.events[0].status, "in_progress")
        self.assertEqual(self.orchestrator.events[1].phase, "extract")
        self.assertEqual(self.orchestrator.events[1].status, "completed")

    def test_can_skip_phase(self):
        """Test checking if a phase can be skipped."""
        # Extract phase - not completed
        self.orchestrator.state.extraction_status = "not_started"
        self.assertFalse(self.orchestrator._can_skip_phase(WorkflowPhase.EXTRACT.value))

        # Extract phase - completed
        self.orchestrator.state.extraction_status = "completed"
        self.assertTrue(self.orchestrator._can_skip_phase(WorkflowPhase.EXTRACT.value))

        # Transform phase - not completed
        self.orchestrator.state.transformation_status = "in_progress"
        self.assertFalse(self.orchestrator._can_skip_phase(WorkflowPhase.TRANSFORM.value))

        # Transform phase - completed
        self.orchestrator.state.transformation_status = "completed"
        self.assertTrue(self.orchestrator._can_skip_phase(WorkflowPhase.TRANSFORM.value))

        # Load phase - not completed
        self.orchestrator.state.loading_status = "failed"
        self.assertFalse(self.orchestrator._can_skip_phase(WorkflowPhase.LOAD.value))

        # Load phase - completed
        self.orchestrator.state.loading_status = "completed"
        self.assertTrue(self.orchestrator._can_skip_phase(WorkflowPhase.LOAD.value))

        # Validate phase - always run
        self.assertFalse(self.orchestrator._can_skip_phase(WorkflowPhase.VALIDATE.value))

    def test_generate_workflow_summary(self):
        """Test generating a workflow summary."""
        # Set up mock state
        self.orchestrator.state.extraction_status = "completed"
        self.orchestrator.state.transformation_status = "completed"
        self.orchestrator.state.loading_status = "in_progress"

        # Mock entity counts
        self.mock_db.get_source_entity_counts.return_value = {"test_cases": 100, "test_cycles": 10}
        self.mock_db.get_target_entity_counts.return_value = {"test_cases": 80, "test_cycles": 5}
        self.mock_db.get_entity_mapping_counts.return_value = {"test_cases": 80, "test_cycles": 5}

        # Create some events with timestamps for duration calculation
        extract_start = WorkflowEvent(
            phase="extract",
            status="in_progress",
            message="Starting extract",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )
        extract_end = WorkflowEvent(
            phase="extract",
            status="completed",
            message="Extract completed",
            timestamp=datetime(2025, 1, 1, 12, 5, 0),  # 5 minutes later
        )
        self.orchestrator.events = [extract_start, extract_end]

        # Generate summary
        summary = self.orchestrator._generate_workflow_summary()

        # Check summary content
        self.assertEqual(summary["project_key"], "TEST")
        self.assertEqual(summary["extraction_status"], "completed")
        self.assertEqual(summary["transformation_status"], "completed")
        self.assertEqual(summary["loading_status"], "in_progress")
        self.assertEqual(summary["events_count"], 2)

        # Check duration calculation
        self.assertEqual(summary["duration"]["extract"], 300.0)  # 5 minutes = 300 seconds

        # Check entity counts
        self.assertEqual(summary["entity_counts"]["source"]["test_cases"], 100)
        self.assertEqual(summary["entity_counts"]["target"]["test_cases"], 80)
        self.assertEqual(summary["entity_counts"]["mappings"]["test_cases"], 80)

    def test_get_workflow_status(self):
        """Test getting workflow status."""
        # Set up mock state
        self.orchestrator.state.extraction_status = "completed"
        self.orchestrator.state.transformation_status = "in_progress"
        self.orchestrator.state.loading_status = "not_started"

        # Mock database methods
        self.mock_db.get_source_entity_counts.return_value = {"test_cases": 100}
        self.mock_db.get_target_entity_counts.return_value = {"test_cases": 50}
        self.mock_db.get_entity_mapping_counts.return_value = {"test_cases": 50}
        self.mock_db.get_incomplete_batches.return_value = []

        # Add some events
        self.orchestrator.events = [
            WorkflowEvent(phase="extract", status="completed", message="Extract completed"),
            WorkflowEvent(phase="transform", status="in_progress", message="Transform started"),
        ]

        # Get status
        status = self.orchestrator.get_workflow_status()

        # Check status content
        self.assertEqual(status["project_key"], "TEST")
        self.assertEqual(status["phases"]["extract"], "completed")
        self.assertEqual(status["phases"]["transform"], "in_progress")
        self.assertEqual(status["phases"]["load"], "not_started")

        # Check entity counts
        self.assertEqual(status["entity_counts"]["source"]["test_cases"], 100)
        self.assertEqual(status["entity_counts"]["target"]["test_cases"], 50)

        # Check events
        self.assertEqual(len(status["events"]), 2)
        self.assertEqual(status["events"][0]["phase"], "extract")
        self.assertEqual(status["events"][1]["phase"], "transform")


if __name__ == "__main__":
    unittest.main()
