#!/usr/bin/env python3
"""
Example showing how to use the enhanced validation framework during migration.

This example demonstrates how to create a migration instance with validation enabled
and how to view validation reports and issues after the migration.
"""

import argparse
import logging
import sys
from pathlib import Path

from ztoq.database_manager import DatabaseManager
from ztoq.migration import create_migration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.validation import ValidationLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("validation_example")


def run_migration_with_validation(
    zephyr_url, zephyr_api_key, zephyr_project_key, qtest_url, qtest_api_key, qtest_project_id
):
    """Run a migration with validation enabled."""
    # Create configurations
    zephyr_config = ZephyrConfig(
        api_url=zephyr_url, api_key=zephyr_api_key, project_key=zephyr_project_key
    )
    
    qtest_config = QTestConfig(
        api_url=qtest_url, api_key=qtest_api_key, project_id=qtest_project_id
    )
    
    # Initialize database
    db_path = Path(f"./migration_{zephyr_project_key}_validated.db")
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_database()
    
    # Create migration instance with validation enabled
    migration = create_migration(
        zephyr_config=zephyr_config,
        qtest_config=qtest_config,
        database_manager=db_manager,
        batch_size=50,
        max_workers=3,
        attachments_dir=Path(f"./attachments_{zephyr_project_key}"),
        enable_validation=True,  # Enable validation
    )
    
    # Run migration
    try:
        migration.run_migration()
        logger.info(f"Migration for project {zephyr_project_key} completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        
    # Display validation results
    display_validation_results(db_manager, zephyr_project_key)


def display_validation_results(db_manager, project_key):
    """Display validation results after migration."""
    # Get latest validation report
    reports = db_manager.get_validation_reports(project_key, limit=1)
    if reports:
        report = reports[0]
        logger.info(f"Validation Report Summary: {report['summary']}")
        
        # Display issue counts by level
        issue_counts = report.get("issue_counts", {})
        logger.info("Issue counts by level:")
        for level, count in issue_counts.items():
            logger.info(f"  {level}: {count}")
        
        # Get critical issues
        critical_issues = db_manager.get_validation_issues(
            project_key, resolved=False, level=ValidationLevel.CRITICAL.value
        )
        if critical_issues:
            logger.warning(f"Found {len(critical_issues)} CRITICAL issues:")
            for issue in critical_issues:
                logger.warning(f"  - {issue['message']} ({issue['entity_id']})")
        
        # Get error issues
        error_issues = db_manager.get_validation_issues(
            project_key, resolved=False, level=ValidationLevel.ERROR.value
        )
        if error_issues:
            logger.error(f"Found {len(error_issues)} ERROR issues:")
            for issue in error_issues:
                logger.error(f"  - {issue['message']} ({issue['entity_id']})")
    else:
        logger.info("No validation reports found")


def main():
    """Run the example."""
    parser = argparse.ArgumentParser(description="Run a migration with validation")
    parser.add_argument("--zephyr-url", required=True, help="Zephyr API URL")
    parser.add_argument("--zephyr-api-key", required=True, help="Zephyr API key")
    parser.add_argument("--zephyr-project-key", required=True, help="Zephyr project key")
    parser.add_argument("--qtest-url", required=True, help="qTest API URL")
    parser.add_argument("--qtest-api-key", required=True, help="qTest API key")
    parser.add_argument("--qtest-project-id", required=True, help="qTest project ID")
    
    args = parser.parse_args()
    
    run_migration_with_validation(
        args.zephyr_url,
        args.zephyr_api_key,
        args.zephyr_project_key,
        args.qtest_url,
        args.qtest_api_key,
        args.qtest_project_id,
    )


if __name__ == "__main__":
    main()