#!/usr/bin/env python3
"""
Example demonstrating how to create a custom migration with specialized mapping logic.

This example shows how to extend the ZephyrToQTestMigration class to implement:
1. Custom entity mapping logic
2. Custom field transformations
3. Specialized handling for attachments
4. Custom error handling and retry logic

You can run this with:
    poetry run python examples/custom_migration.py
"""

import logging
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path to import ztoq modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from ztoq.migration import ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig, QTestModule, QTestTestCase, QTestTestCycle

# Configure logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("custom_migration")


class CustomFieldMapping(Enum):
    """Mapping of Zephyr custom fields to qTest custom fields."""
    
    # Standard mappings - same name in both systems
    COMPONENT = "component"
    PRIORITY = "priority"
    OWNER = "owner"
    
    # Custom mappings - different names or special handling
    ZEPHYR_TEST_TYPE = "test_type"  # Maps to qTest "testType"
    ZEPHYR_AUTOMATION_STATUS = "automation_status"  # Maps to qTest "automationStatus"
    ZEPHYR_BUG_ID = "bug_id"  # Maps to qTest "defectId"
    
    # Fields to ignore - don't map these
    IGNORE_DEPRECATED = "deprecated"
    IGNORE_INTERNAL_ID = "internal_id"


class CustomZephyrToQTestMigration(ZephyrToQTestMigration):
    """Custom migration class with specialized mapping logic."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with additional custom configuration."""
        # Extract custom parameters before passing to parent
        self.retry_attempts = kwargs.pop("retry_attempts", 3)
        self.retry_delay = kwargs.pop("retry_delay", 5)
        self.custom_field_mapping = kwargs.pop("custom_field_mapping", {})
        self.auto_create_folders = kwargs.pop("auto_create_folders", True)
        
        # Call parent constructor
        super().__init__(*args, **kwargs)
        
        # Add extra mappings
        self.priority_mapping = {
            "highest": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "lowest": 5,
            # Add custom mappings
            "critical": 1,
            "major": 2,
            "normal": 3,
            "minor": 4,
            "trivial": 5,
        }
        
        # Add custom status mapping
        self.status_mapping = {
            "pass": "PASSED",
            "fail": "FAILED",
            "wip": "IN_PROGRESS",
            "blocked": "BLOCKED",
            "unexecuted": "NOT_RUN",
            # Add custom mappings
            "approved": "PASSED",
            "rejected": "FAILED",
            "pending": "IN_PROGRESS",
            "cancelled": "BLOCKED",
        }
    
    def _map_priority(self, zephyr_priority: str) -> int:
        """Override parent method with more comprehensive mapping."""
        # Use our expanded mapping table
        return self.priority_mapping.get(zephyr_priority.lower(), 3)  # Default to medium
    
    def _map_status(self, zephyr_status: str) -> str:
        """Override parent method with more comprehensive status mapping."""
        # Use our expanded status mapping table
        return self.status_mapping.get(zephyr_status.lower(), "NOT_RUN")
    
    def _transform_custom_fields(self, zephyr_custom_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform Zephyr custom fields to qTest format with custom mapping."""
        qtest_fields = []
        
        # Process each Zephyr custom field
        for field_name, field_value in zephyr_custom_fields.items():
            # Skip ignored fields
            if field_name in [e.value for e in CustomFieldMapping if e.name.startswith("IGNORE_")]:
                logger.debug(f"Skipping ignored field: {field_name}")
                continue
            
            # Get qTest field name from mapping or use the original
            qtest_field_name = self.custom_field_mapping.get(field_name, field_name)
            
            # Handle field type based on value
            field_type = "STRING"
            if isinstance(field_value, bool):
                field_type = "BOOLEAN"
                field_value = str(field_value).lower()  # Convert to "true" or "false"
            elif isinstance(field_value, (int, float)):
                field_type = "NUMBER"
                field_value = str(field_value)
            elif field_value is None:
                # Skip null fields
                continue
            else:
                field_value = str(field_value)
            
            # Create qTest custom field
            qtest_field = {
                "field_name": qtest_field_name,
                "field_type": field_type,
                "field_value": field_value,
            }
            
            qtest_fields.append(qtest_field)
        
        return qtest_fields
    
    def _transform_test_cases(self):
        """Override parent method to apply custom field transformation."""
        logger.info("Transforming test cases with custom field mapping")
        
        # Get test cases from database with their steps
        test_cases = self.db.get_test_cases_with_steps(self.zephyr_config.project_key)
        
        # Initialize batch tracking
        test_case_tracker = self._create_batch_tracker("transformed_test_cases", len(test_cases))
        
        # Process test cases in batches
        for batch_idx, batch in enumerate(self._create_batches(test_cases)):
            try:
                transformed_batch = []
                
                for test_case in batch:
                    # Get module ID for the test case's folder
                    module_id = None
                    folder_id = test_case.get("folderId")
                    
                    if folder_id:
                        module_mapping = self.db.get_entity_mapping(
                            self.zephyr_config.project_key, "folder_to_module", folder_id
                        )
                        if module_mapping:
                            module_id = module_mapping.get("target_id")
                        elif self.auto_create_folders:
                            # Auto-create missing folder mapping
                            logger.info(f"Auto-creating module mapping for folder {folder_id}")
                            folder = self.db.get_folder(self.zephyr_config.project_key, folder_id)
                            if folder:
                                # Create a new module in qTest (in real code, you would call the API)
                                module = QTestModule(
                                    name=folder.get("name", f"Folder {folder_id}"),
                                    description=f"Auto-created from Zephyr folder: {folder_id}",
                                )
                                # In real code: module_id = self.qtest_client.create_module(module).id
                                module_id = f"auto_module_{folder_id}"
                                
                                # Save mapping
                                self.db.save_entity_mapping(
                                    self.zephyr_config.project_key, "folder_to_module", folder_id, module_id
                                )
                    
                    # Transform test steps - existing logic from parent class
                    qtest_steps = []
                    steps = test_case.get("steps", [])
                    
                    for idx, step in enumerate(steps):
                        qtest_step = {
                            "description": step.get("description", ""),
                            "expected_result": step.get("expectedResult", ""),
                            "order": idx + 1,
                        }
                        qtest_steps.append(qtest_step)
                    
                    # Transform custom fields with our custom logic
                    qtest_custom_fields = self._transform_custom_fields(test_case.get("customFields", {}))
                    
                    # Create qTest test case
                    qtest_test_case = QTestTestCase(
                        name=test_case.get("name", ""),
                        description=test_case.get("description", ""),
                        precondition=test_case.get("precondition", ""),
                        test_steps=qtest_steps,
                        properties=qtest_custom_fields,
                        module_id=module_id,
                        priority_id=self._map_priority(test_case.get("priority", "")),
                    )
                    
                    # Save transformed test case
                    self.db.save_transformed_test_case(
                        self.zephyr_config.project_key, test_case.get("id"), qtest_test_case
                    )
                    
                    transformed_batch.append(qtest_test_case)
                
                # Update batch status
                self._update_batch_status(test_case_tracker, batch_idx, len(batch), "completed")
                
            except Exception as e:
                # Update batch status with error
                self._update_batch_status(test_case_tracker, batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to transform test case batch {batch_idx}: {str(e)}")
        
        logger.info(f"Transformed {len(test_cases)} test cases")
    
    def _create_test_case_in_qtest(self, source_id, test_case_data):
        """Create a test case in qTest with retry logic."""
        retry_count = 0
        
        while retry_count < self.retry_attempts:
            try:
                # Create QTestTestCase object from data
                test_case = QTestTestCase(
                    name=test_case_data.get("name", ""),
                    description=test_case_data.get("description", ""),
                    precondition=test_case_data.get("precondition", ""),
                    test_steps=test_case_data.get("test_steps", []),
                    properties=test_case_data.get("properties", []),
                    module_id=test_case_data.get("module_id"),
                    priority_id=test_case_data.get("priority_id"),
                )
                
                # Create in qTest - in a real implementation, this would call the API
                # For this example, we're just mocking the result
                created_test_case = QTestTestCase(
                    id=f"qtc-{source_id}",
                    name=test_case.name,
                    description=test_case.description,
                    precondition=test_case.precondition,
                    test_steps=test_case.test_steps,
                    properties=test_case.properties,
                    module_id=test_case.module_id,
                    priority_id=test_case.priority_id,
                )
                
                logger.debug(f"Created test case {created_test_case.id} for source case {source_id}")
                return created_test_case
                
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Error creating test case for source {source_id}: {str(e)}. "
                    f"Retry {retry_count}/{self.retry_attempts}"
                )
                
                if retry_count < self.retry_attempts:
                    # Wait before retrying
                    time.sleep(self.retry_delay)
                else:
                    # All retries exhausted
                    logger.error(f"Failed to create test case after {self.retry_attempts} attempts")
                    raise
    
    def _create_batches(self, items: List[Any]) -> List[List[Any]]:
        """Split items into batches of the configured batch size."""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batches.append(items[i:i + self.batch_size])
        return batches
    
    def _create_batch_tracker(self, entity_type: str, total_items: int):
        """Create a batch tracker for an entity type."""
        tracker = EntityBatchTracker(self.zephyr_config.project_key, entity_type, self.db)
        tracker.initialize_batches(total_items, self.batch_size)
        return tracker
    
    def _update_batch_status(self, tracker, batch_idx, processed_count, status, error=None):
        """Update a batch's status."""
        tracker.update_batch_status(batch_idx, processed_count, status, error)


def run_custom_migration_example():
    """Run the custom migration example."""
    console.print("[bold green]Custom Migration Example[/bold green]")
    console.print("This example shows how to extend the migration framework with custom logic.\n")
    
    # In a real application, you would get these from configuration or environment variables
    zephyr_config = ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="YOUR_ZEPHYR_API_TOKEN",  # Don't hardcode in real code!
        project_key="DEMO",
    )
    
    qtest_config = QTestConfig(
        base_url="https://example.qtest.com",
        username="your_qtest_username",
        password="your_qtest_password",  # Don't hardcode in real code!
        project_id=12345,
    )
    
    # Custom field mapping
    custom_field_mapping = {
        "test_type": "testType",
        "automation_status": "automationStatus",
        "bug_id": "defectId",
        "requirement": "requirementId",
        "component": "component",
        # Add more mappings as needed
    }
    
    # Create a mock database manager
    db_manager = MagicMock()
    
    # Configure the mock database manager with some basic behaviors
    db_manager.get_migration_state.return_value = None
    db_manager.get_entity_mappings.return_value = []
    
    # Create attachment directory
    attachments_dir = Path("./custom_migration_attachments")
    attachments_dir.mkdir(exist_ok=True)
    
    # Create the custom migration instance
    migration = CustomZephyrToQTestMigration(
        zephyr_config=zephyr_config,
        qtest_config=qtest_config,
        database_manager=db_manager,
        batch_size=20,
        max_workers=4,
        attachments_dir=attachments_dir,
        # Custom parameters
        retry_attempts=3,
        retry_delay=2,
        custom_field_mapping=custom_field_mapping,
        auto_create_folders=True,
    )
    
    # In a real application, you would execute the full migration
    # For this example, we just demonstrate some of the custom functionality
    console.print("[bold]Custom field mapping examples:[/bold]")
    
    # Show priority mapping
    console.print("\n[bold]Priority mapping examples:[/bold]")
    priorities = ["highest", "high", "medium", "low", "lowest", "critical", "major", "normal", "minor", "trivial"]
    for priority in priorities:
        mapped = migration._map_priority(priority)
        console.print(f"  Zephyr '{priority}' -> qTest priority ID {mapped}")
    
    # Show status mapping
    console.print("\n[bold]Status mapping examples:[/bold]")
    statuses = ["pass", "fail", "wip", "blocked", "unexecuted", "approved", "rejected", "pending", "cancelled"]
    for status in statuses:
        mapped = migration._map_status(status)
        console.print(f"  Zephyr '{status}' -> qTest '{mapped}'")
    
    # Show custom field transformation
    console.print("\n[bold]Custom field transformation example:[/bold]")
    zephyr_fields = {
        "test_type": "API",
        "automation_status": "Automated",
        "bug_id": "BUG-123",
        "component": "Backend",
        "priority": "High",
        "deprecated": True,  # This should be ignored
        "internal_id": "12345",  # This should be ignored
    }
    
    transformed = migration._transform_custom_fields(zephyr_fields)
    console.print("  Zephyr fields:")
    for k, v in zephyr_fields.items():
        console.print(f"    - {k}: {v}")
    
    console.print("  Transformed qTest fields:")
    for field in transformed:
        console.print(f"    - {field['field_name']}: {field['field_value']} ({field['field_type']})")
    
    console.print("\n[bold]This is just an example - in a real application, you would run:[/bold]")
    console.print("  migration.run_migration()")


# Mock the database manager for the example - in a real application, you'd implement all required methods
from unittest.mock import MagicMock

if __name__ == "__main__":
    run_custom_migration_example()