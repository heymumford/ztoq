"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import MagicMock, call

import pytest

from ztoq.migration import EntityBatchTracker


@pytest.mark.unit
class TestEntityBatchTracker:
    """Test the EntityBatchTracker for proper error handling and batch management."""

    @pytest.fixture
    def db_mock(self):
        """Create a mock database manager."""
        db = MagicMock()
        return db
    
    def test_batch_initialization(self, db_mock):
        """Test batch initialization with correct calculations."""
        # Create batch tracker instance
        tracker = EntityBatchTracker("TEST", "test_cases", db_mock)
        
        # Test batch initialization with 25 items and batch size 10
        tracker.initialize_batches(25, 10)
        
        # Verify database calls (should create 3 batches)
        assert db_mock.create_entity_batch.call_count == 3
        db_mock.create_entity_batch.assert_has_calls([
            call("TEST", "test_cases", 0, 3, 10),  # First batch: 10 items
            call("TEST", "test_cases", 1, 3, 10),  # Second batch: 10 items
            call("TEST", "test_cases", 2, 3, 5),   # Third batch: 5 items
        ])
        
    def test_batch_status_updates(self, db_mock):
        """Test updating batch status including error conditions."""
        # Create batch tracker instance
        tracker = EntityBatchTracker("TEST", "test_cases", db_mock)
        
        # Test successful batch update
        tracker.update_batch_status(0, 10, "completed")
        db_mock.update_entity_batch.assert_called_with(
            "TEST", "test_cases", 0, 10, "completed", None
        )
        
        # Test batch update with error
        db_mock.update_entity_batch.reset_mock()
        tracker.update_batch_status(1, 5, "failed", "Database timeout")
        db_mock.update_entity_batch.assert_called_with(
            "TEST", "test_cases", 1, 5, "failed", "Database timeout"
        )
        
        # Test batch update with zero processed items
        db_mock.update_entity_batch.reset_mock()
        tracker.update_batch_status(2, 0, "failed", "API error")
        db_mock.update_entity_batch.assert_called_with(
            "TEST", "test_cases", 2, 0, "failed", "API error"
        )
    
    def test_get_pending_batches(self, db_mock):
        """Test retrieving pending batches with proper filtering."""
        # Create batch tracker instance
        tracker = EntityBatchTracker("TEST", "test_cases", db_mock)
        
        # Set up mock return value for pending batches
        db_mock.get_pending_entity_batches.return_value = [
            {"batch_number": 1, "total_items": 10, "processed_items": 5, "status": "failed"},
            {"batch_number": 2, "total_items": 10, "processed_items": 0, "status": "not_started"}
        ]
        
        # Get pending batches
        pending = tracker.get_pending_batches()
        
        # Verify database was called correctly
        db_mock.get_pending_entity_batches.assert_called_with("TEST", "test_cases")
        
        # Verify result structure
        assert len(pending) == 2
        assert pending[0]["batch_number"] == 1
        assert pending[0]["processed_items"] == 5
        assert pending[1]["batch_number"] == 2
        assert pending[1]["processed_items"] == 0
    
    def test_batch_recovery_workflow(self, db_mock):
        """Test a full recovery workflow for failed batches."""
        # Create batch tracker instance
        tracker = EntityBatchTracker("TEST", "test_cases", db_mock)
        
        # Initialize batches
        tracker.initialize_batches(30, 10)  # 3 batches of 10 items
        
        # Mock scenario where batch 1 failed halfway through
        db_mock.get_pending_entity_batches.return_value = [
            {"batch_number": 1, "total_items": 10, "processed_items": 5, "status": "failed"},
        ]
        
        # Get pending batches for recovery
        pending = tracker.get_pending_batches()
        
        # Verify we found the failed batch
        assert len(pending) == 1
        assert pending[0]["batch_number"] == 1
        assert pending[0]["processed_items"] == 5
        
        # Simulate recovery of the batch
        tracker.update_batch_status(1, 10, "completed")
        
        # Verify the update call
        db_mock.update_entity_batch.assert_called_with(
            "TEST", "test_cases", 1, 10, "completed", None
        )
        
        # Update the mock to show no more pending batches
        db_mock.get_pending_entity_batches.return_value = []
        
        # Check that all batches are now complete
        assert len(tracker.get_pending_batches()) == 0