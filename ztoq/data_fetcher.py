"""
Responsible for fetching all test data from Zephyr Scale API and preparing it for storage.

This module implements a functional approach to data retrieval, with each function handling
a single responsibility. Functions are designed to be composable and to have no side effects
apart from API interactions.
"""

from typing import Dict, List, Any, Optional, Callable, TypeVar, Iterator, Tuple
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ztoq.models import (
    ZephyrConfig, 
    Project, 
    Case, 
    CycleInfo, 
    Plan, 
    Execution,
    Folder,
    Status,
    Priority,
    Environment
)
from ztoq.zephyr_client import ZephyrClient

T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    """Immutable container for fetch operation results."""
    entity_type: str
    project_key: str
    items: List[Any]
    count: int
    success: bool
    error: Optional[str] = None


def create_authenticated_client(config: ZephyrConfig) -> ZephyrClient:
    """
    Creates an authenticated Zephyr client using the provided configuration.
    
    The client handles proper authentication and provides methods for interacting
    with the Zephyr Scale API.
    """
    return ZephyrClient(config)


def fetch_projects(client: ZephyrClient) -> List[Project]:
    """
    Retrieves all available projects from Zephyr Scale.
    
    Projects are the top-level container for all test-related data in Zephyr Scale.
    """
    try:
        logger.info("Fetching all projects")
        return list(client.get_projects())
    except Exception as e:
        logger.error(f"Failed to fetch projects: {str(e)}")
        return []


def fetch_all_test_cases(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all test cases for a specific project.
    
    Test cases are the fundamental building blocks of testing in Zephyr Scale.
    They contain the test steps, expected results, and metadata.
    """
    try:
        logger.info(f"Fetching test cases for project {project_key}")
        test_cases = list(client.get_test_cases(project_key=project_key))
        return FetchResult(
            entity_type="test_cases",
            project_key=project_key,
            items=test_cases,
            count=len(test_cases),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch test cases for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="test_cases",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_all_test_cycles(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all test cycles for a specific project.
    
    Test cycles represent a collection of test executions for a specific timeframe,
    milestone, or release. They provide context for when tests were executed.
    """
    try:
        logger.info(f"Fetching test cycles for project {project_key}")
        test_cycles = list(client.get_test_cycles(project_key=project_key))
        return FetchResult(
            entity_type="test_cycles",
            project_key=project_key,
            items=test_cycles,
            count=len(test_cycles),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch test cycles for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="test_cycles",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_all_test_executions(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all test executions for a specific project.
    
    Test executions represent the actual results of running test cases.
    They include status, comments, attachments, and other execution metadata.
    """
    try:
        logger.info(f"Fetching test executions for project {project_key}")
        test_executions = list(client.get_test_executions(project_key=project_key))
        return FetchResult(
            entity_type="test_executions",
            project_key=project_key,
            items=test_executions,
            count=len(test_executions),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch test executions for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="test_executions",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_folders(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all folders for a specific project.
    
    Folders provide hierarchical organization for test cases and cycles in Zephyr Scale.
    """
    try:
        logger.info(f"Fetching folders for project {project_key}")
        folders = client.get_folders(project_key=project_key)
        return FetchResult(
            entity_type="folders",
            project_key=project_key,
            items=folders,
            count=len(folders),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch folders for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="folders",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_statuses(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all statuses for a specific project.
    
    Statuses define the possible states for test cases and executions,
    such as Pass, Fail, Blocked, etc.
    """
    try:
        logger.info(f"Fetching statuses for project {project_key}")
        statuses = client.get_statuses(project_key=project_key)
        return FetchResult(
            entity_type="statuses",
            project_key=project_key,
            items=statuses,
            count=len(statuses),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch statuses for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="statuses",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_priorities(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all priorities for a specific project.
    
    Priorities indicate the importance level of test cases (e.g., High, Medium, Low).
    """
    try:
        logger.info(f"Fetching priorities for project {project_key}")
        priorities = client.get_priorities(project_key=project_key)
        return FetchResult(
            entity_type="priorities",
            project_key=project_key,
            items=priorities,
            count=len(priorities),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch priorities for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="priorities",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_environments(client: ZephyrClient, project_key: str) -> FetchResult:
    """
    Retrieves all environments for a specific project.
    
    Environments define the testing context (e.g., Production, Staging, Dev)
    where test executions take place.
    """
    try:
        logger.info(f"Fetching environments for project {project_key}")
        environments = client.get_environments(project_key=project_key)
        return FetchResult(
            entity_type="environments",
            project_key=project_key,
            items=environments,
            count=len(environments),
            success=True
        )
    except Exception as e:
        error_message = f"Failed to fetch environments for project {project_key}: {str(e)}"
        logger.error(error_message)
        return FetchResult(
            entity_type="environments",
            project_key=project_key,
            items=[],
            count=0,
            success=False,
            error=error_message
        )


def fetch_all_project_data(
    client: ZephyrClient, 
    project_key: str,
    progress_callback: Optional[Callable[[str, str, bool], None]] = None
) -> Dict[str, FetchResult]:
    """
    Retrieves all test data for a specific project using parallel processing.
    
    This function coordinates the fetching of all data types in parallel
    to optimize retrieval time. It uses ThreadPoolExecutor to manage concurrent
    API requests while maintaining thread safety.
    
    Args:
        client: The authenticated Zephyr client
        project_key: The project key to fetch data for
        progress_callback: Optional callback to report progress
        
    Returns:
        Dictionary mapping entity types to their fetch results
    """
    fetch_functions = {
        "test_cases": lambda: fetch_all_test_cases(client, project_key),
        "test_cycles": lambda: fetch_all_test_cycles(client, project_key),
        "test_executions": lambda: fetch_all_test_executions(client, project_key),
        "folders": lambda: fetch_folders(client, project_key),
        "statuses": lambda: fetch_statuses(client, project_key),
        "priorities": lambda: fetch_priorities(client, project_key),
        "environments": lambda: fetch_environments(client, project_key)
    }
    
    results: Dict[str, FetchResult] = {}
    
    # Execute all fetch operations in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Start all fetch tasks
        future_to_entity = {
            executor.submit(fetch_func): entity_type
            for entity_type, fetch_func in fetch_functions.items()
        }
        
        # Process results as they complete
        for future in as_completed(future_to_entity):
            entity_type = future_to_entity[future]
            try:
                result = future.result()
                results[entity_type] = result
                if progress_callback:
                    progress_callback(
                        entity_type, 
                        project_key,
                        result.success
                    )
            except Exception as e:
                logger.error(f"Error in fetch operation for {entity_type}: {str(e)}")
                if progress_callback:
                    progress_callback(entity_type, project_key, False)
    
    return results


def fetch_all_projects_data(
    client: ZephyrClient,
    project_keys: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[str, str, bool], None]] = None
) -> Dict[str, Dict[str, FetchResult]]:
    """
    Retrieves all test data for multiple projects.
    
    When project_keys is None, it fetches projects first and then retrieves
    data for all available projects.
    
    Args:
        client: The authenticated Zephyr client
        project_keys: Optional list of project keys to fetch data for
        progress_callback: Optional callback to report progress
        
    Returns:
        Dictionary mapping project keys to their respective data results
    """
    # If no project keys provided, fetch all projects first
    if not project_keys:
        projects = fetch_projects(client)
        project_keys = [project.key for project in projects]
    
    results: Dict[str, Dict[str, FetchResult]] = {}
    
    for project_key in project_keys:
        logger.info(f"Fetching all data for project {project_key}")
        if progress_callback:
            progress_callback("project_start", project_key, True)
            
        project_results = fetch_all_project_data(
            client, 
            project_key,
            progress_callback
        )
        
        results[project_key] = project_results
        
        if progress_callback:
            # Count successful entities
            success_count = sum(1 for result in project_results.values() if result.success)
            progress_callback(
                "project_complete", 
                project_key,
                success_count == len(project_results)
            )
    
    return results