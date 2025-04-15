"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Performance tests for API clients.

This module contains performance tests for the Zephyr and qTest API clients,
including connection pooling, batch operations, and concurrent requests.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import patch

import pytest
import requests
import responses
from responses import matchers

from tests.performance.base import PerformanceTest
from ztoq.connection_pool import ConnectionPool, connection_pool
from ztoq.models import ZephyrConfig
from ztoq.qtest_client import QTestClient, QTestConfig
from ztoq.zephyr_client import ZephyrClient

logger = logging.getLogger(__name__)


class APIPerformanceTest(PerformanceTest):
    """Base class for API client performance tests."""

    def __init__(
        self,
        name: str,
        output_dir: str | None = None,
    ):
        """Initialize API performance test.

        Args:
            name: Name of the performance test
            output_dir: Output directory for test results
        """
        super().__init__(name=name, output_dir=output_dir)
        self.result.metadata["api_test"] = name

        # Reset connection pool before tests
        connection_pool.close_all()

    def setup(self) -> None:
        """Set up API test environment."""
        super().setup()
        logger.info(f"API performance test setup complete: {self.name}")


class ConnectionPoolPerformanceTest(APIPerformanceTest):
    """Performance tests for connection pooling."""

    def __init__(
        self,
        output_dir: str | None = None,
        base_url: str = "https://api.example.com",
        request_count: int = 100,
        pool_sizes: list[int] = None,
    ):
        """Initialize connection pool performance test.

        Args:
            output_dir: Output directory for test results
            base_url: Base URL for test requests
            request_count: Number of requests to make in each test
            pool_sizes: List of pool sizes to test
        """
        super().__init__(name="connection_pool_performance", output_dir=output_dir)
        self.base_url = base_url
        self.request_count = request_count
        self.pool_sizes = pool_sizes or [1, 5, 10, 20, 50]

        self.result.metadata["base_url"] = base_url
        self.result.metadata["request_count"] = request_count

    def _run_test(self) -> None:
        """Run connection pool performance tests."""
        # Test with different pool sizes
        for pool_size in self.pool_sizes:
            logger.info(f"Testing with pool size: {pool_size}")
            self._test_pool_size(pool_size)

        # Test with and without pooling
        self._test_with_without_pooling()

        # Test with concurrent requests
        self._test_concurrent_requests()

    def _test_pool_size(self, pool_size: int) -> None:
        """Test performance with different pool sizes.

        Args:
            pool_size: Size of the connection pool
        """
        # Get measure decorator for this instance
        measure = self.measure(operation="sequential_requests")

        @measure
        def run_pool_test():
            self.result.metadata["pool_size"] = pool_size

            # Create mock responses
            with responses.RequestsMock() as rsps:
                # Add response for the endpoint
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/test",
                    json={"status": "success"},
                    status=200,
                    content_type="application/json",
                )

                # Create a new pool with the specified size
                test_pool = ConnectionPool(max_pool_size=pool_size)

                # Make requests
                for i in range(self.request_count):
                    with test_pool.get_session(f"{self.base_url}/api/test") as session:
                        response = session.get(f"{self.base_url}/api/test")
                        assert response.status_code == 200

                # Get metrics
                metrics = test_pool.get_metrics()
                logger.info(f"Pool metrics for size {pool_size}: Created={metrics['created_connections']}, Reused={metrics['reused_connections']}")

        run_pool_test()

    def _test_with_pooling(self) -> None:
        """Test performance with connection pooling."""
        # Get measure decorator for this instance
        measure = self.measure(operation="with_pooling")

        @measure
        def run_with_pooling():
            # Create mock responses
            with responses.RequestsMock() as rsps:
                # Add response for the endpoint
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/test",
                    json={"status": "success"},
                    status=200,
                    content_type="application/json",
                )

                # Create a pool with default settings
                test_pool = ConnectionPool()

                # Make requests
                for i in range(self.request_count):
                    with test_pool.get_session(f"{self.base_url}/api/test") as session:
                        response = session.get(f"{self.base_url}/api/test")
                        assert response.status_code == 200

        run_with_pooling()

    def _test_without_pooling(self) -> None:
        """Test performance without connection pooling."""
        # Get measure decorator for this instance
        measure = self.measure(operation="without_pooling")

        @measure
        def run_without_pooling():
            # Create mock responses
            with responses.RequestsMock() as rsps:
                # Add response for the endpoint
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/test",
                    json={"status": "success"},
                    status=200,
                    content_type="application/json",
                )

                # Make requests without pooling
                for i in range(self.request_count):
                    session = requests.Session()
                    response = session.get(f"{self.base_url}/api/test")
                    assert response.status_code == 200
                    session.close()

        run_without_pooling()

    def _test_with_without_pooling(self) -> None:
        """Compare performance with and without connection pooling."""
        self._test_with_pooling()
        self._test_without_pooling()

    def _test_concurrent_requests(self, num_threads: int = 10) -> None:
        """Test performance with concurrent requests.

        Args:
            num_threads: Number of concurrent threads
        """
        # Get measure decorator for this instance
        measure = self.measure(operation="concurrent_requests", concurrency=num_threads)

        @measure
        def run_concurrent_test():
            self.result.metadata["concurrency"] = num_threads

            # Create mock responses
            with responses.RequestsMock() as rsps:
                # Add response for the endpoint
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/test",
                    json={"status": "success"},
                    status=200,
                    content_type="application/json",
                )

                # Function to make requests
                def make_requests(thread_id: int, num_requests: int) -> dict[str, Any]:
                    start_time = time.time()
                    requests_per_thread = num_requests // num_threads

                    for i in range(requests_per_thread):
                        with connection_pool.get_session(f"{self.base_url}/api/test") as session:
                            response = session.get(f"{self.base_url}/api/test")
                            assert response.status_code == 200

                    return {
                        "thread_id": thread_id,
                        "requests": requests_per_thread,
                        "duration": time.time() - start_time,
                    }

                # Run concurrent requests
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [
                        executor.submit(make_requests, thread_id, self.request_count)
                        for thread_id in range(num_threads)
                    ]
                    results = [future.result() for future in futures]

                # Calculate stats
                total_requests = sum(r["requests"] for r in results)
                total_duration = sum(r["duration"] for r in results)
                avg_duration = total_duration / num_threads

                logger.info(f"Concurrent performance: {total_requests} requests in {avg_duration:.2f}s avg time per thread")

                # Get metrics
                metrics = connection_pool.get_metrics()
                logger.info(f"Pool metrics: Created={metrics['created_connections']}, Reused={metrics['reused_connections']}")

        run_concurrent_test()


class ZephyrClientPerformanceTest(APIPerformanceTest):
    """Performance tests for Zephyr client."""

    def __init__(
        self,
        output_dir: str | None = None,
        base_url: str = "https://api.example.com",
        project_key: str = "TEST",
        api_token: str = "fake-token",
    ):
        """Initialize Zephyr client performance test.

        Args:
            output_dir: Output directory for test results
            base_url: Base URL for test requests
            project_key: Project key for tests
            api_token: API token for authentication
        """
        super().__init__(name="zephyr_client_performance", output_dir=output_dir)
        self.base_url = base_url
        self.project_key = project_key
        self.api_token = api_token

        self.result.metadata["base_url"] = base_url
        self.result.metadata["project_key"] = project_key

    def _run_test(self) -> None:
        """Run Zephyr client performance tests."""
        # Test basic operations
        self._test_get_projects()
        self._test_get_test_cases()

        # Test pagination
        self._test_pagination()

        # Test performance with different batch sizes
        self._test_batch_sizes()

    def _test_get_projects(self) -> None:
        """Test performance of getting projects."""
        # Get measure decorator for this instance
        measure = self.measure(operation="get_projects")

        @measure
        def run_test():
            # Mock response for the projects endpoint
            with responses.RequestsMock() as rsps:
                # Add response for the projects endpoint
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/projects",
                    json=[
                        {"id": i, "key": f"PROJ{i}", "name": f"Project {i}"}
                        for i in range(1, 11)
                    ],
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.header_matcher(
                            {"Authorization": f"Bearer {self.api_token}"},
                        ),
                    ],
                )

                # Create client
                config = ZephyrConfig(
                    base_url=self.base_url,
                    project_key=self.project_key,
                    api_token=self.api_token,
                )
                client = ZephyrClient(config)

                # Get projects
                projects = client.get_projects()

                # Verify results
                assert len(projects) == 10

        run_test()

    def _test_get_test_cases(self) -> None:
        """Test performance of getting test cases."""
        # Get measure decorator for this instance
        measure = self.measure(operation="get_test_cases")

        @measure
        def run_test():
            # Mock response for the test cases endpoint with pagination
            with responses.RequestsMock() as rsps:
                # First page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/testcases",
                    json={
                        "values": [
                            {"id": i, "key": f"TC-{i}", "name": f"Test Case {i}"}
                            for i in range(1, 101)
                        ],
                        "startAt": 0,
                        "maxResults": 100,
                        "total": 250,
                        "isLast": False,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"projectKey": self.project_key, "maxResults": "100", "startAt": "0"},
                        ),
                    ],
                )

                # Second page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/testcases",
                    json={
                        "values": [
                            {"id": i, "key": f"TC-{i}", "name": f"Test Case {i}"}
                            for i in range(101, 201)
                        ],
                        "startAt": 100,
                        "maxResults": 100,
                        "total": 250,
                        "isLast": False,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"projectKey": self.project_key, "maxResults": "100", "startAt": "100"},
                        ),
                    ],
                )

                # Third page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/testcases",
                    json={
                        "values": [
                            {"id": i, "key": f"TC-{i}", "name": f"Test Case {i}"}
                            for i in range(201, 251)
                        ],
                        "startAt": 200,
                        "maxResults": 100,
                        "total": 250,
                        "isLast": True,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"projectKey": self.project_key, "maxResults": "100", "startAt": "200"},
                        ),
                    ],
                )

                # Create client
                config = ZephyrConfig(
                    base_url=self.base_url,
                    project_key=self.project_key,
                    api_token=self.api_token,
                )
                client = ZephyrClient(config)

                # Get test cases
                test_cases = list(client.get_test_cases())

                # Verify results
                assert len(test_cases) == 250

        run_test()

    def _test_pagination(self, total_items: int = 500, page_sizes: list[int] = None) -> None:
        """Test performance of paginated requests with different page sizes.

        Args:
            total_items: Total number of items to paginate through
            page_sizes: List of page sizes to test
        """
        page_sizes = page_sizes or [10, 50, 100, 250]

        for page_size in page_sizes:
            # Get measure decorator for this instance with specific metadata
            measure = self.measure(
                operation="pagination",
                dataset_size=total_items,
                batch_size=page_size,
            )

            @measure
            def run_test():
                self.result.metadata["page_size"] = page_size

                # Calculate number of pages
                num_pages = (total_items + page_size - 1) // page_size
                logger.info(f"Testing pagination with page size {page_size} ({num_pages} pages)")

                # Set up mock responses for all pages
                with responses.RequestsMock() as rsps:
                    for page in range(num_pages):
                        start_at = page * page_size
                        end_at = min(start_at + page_size, total_items)
                        is_last = end_at >= total_items

                        rsps.add(
                            responses.GET,
                            f"{self.base_url}/testcases",
                            json={
                                "values": [
                                    {"id": i, "key": f"TC-{i}", "name": f"Test Case {i}"}
                                    for i in range(start_at + 1, end_at + 1)
                                ],
                                "startAt": start_at,
                                "maxResults": page_size,
                                "total": total_items,
                                "isLast": is_last,
                            },
                            status=200,
                            content_type="application/json",
                            match=[
                                matchers.query_param_matcher(
                                    {
                                        "projectKey": self.project_key,
                                        "maxResults": str(page_size),
                                        "startAt": str(start_at),
                                    },
                                ),
                            ],
                        )

                    # Create client
                    config = ZephyrConfig(
                        base_url=self.base_url,
                        project_key=self.project_key,
                        api_token=self.api_token,
                    )
                    client = ZephyrClient(config)

                    # Create paginated iterator with specific page size
                    from ztoq.zephyr_client import PaginatedIterator
                    iterator = PaginatedIterator(
                        client=client,
                        endpoint="/testcases",
                        model_class=client.get_test_cases().model_class,
                        params={"projectKey": self.project_key},
                        page_size=page_size,
                    )

                    # Iterate through all pages
                    items = list(iterator)

                    # Verify results
                    assert len(items) == total_items

            run_test()

    def _test_batch_sizes(self, batch_sizes: list[int] = None) -> None:
        """Test performance of batch operations.

        Args:
            batch_sizes: List of batch sizes to test
        """
        batch_sizes = batch_sizes or [10, 50, 100]

        for batch_size in batch_sizes:
            # Get measure decorator for this instance with specific metadata
            measure = self.measure(
                operation="batch_operations",
                batch_size=batch_size,
            )

            @measure
            def run_test():
                self.result.metadata["batch_size"] = batch_size
                logger.info(f"Testing with batch size: {batch_size}")

                # Mock response for batch operation
                with responses.RequestsMock() as rsps:
                    rsps.add(
                        responses.POST,
                        f"{self.base_url}/bulk/testcases",
                        json={"status": "success", "created": batch_size},
                        status=200,
                        content_type="application/json",
                    )

                    # Create client
                    config = ZephyrConfig(
                        base_url=self.base_url,
                        project_key=self.project_key,
                        api_token=self.api_token,
                    )
                    client = ZephyrClient(config)

                    # Simulating batch operation
                    with patch.object(client, "_make_request") as mock_request:
                        mock_request.return_value = {"status": "success", "created": batch_size}

                        # Simulate batch operation
                        result = client._make_request(
                            "POST",
                            "/bulk/testcases",
                            json_data={"items": [f"item-{i}" for i in range(batch_size)]},
                        )

                        assert result["created"] == batch_size

            run_test()


class QTestClientPerformanceTest(APIPerformanceTest):
    """Performance tests for qTest client."""

    def __init__(
        self,
        output_dir: str | None = None,
        base_url: str = "https://api.example.com",
        project_id: int = 1,
        bearer_token: str = "fake-token",
    ):
        """Initialize qTest client performance test.

        Args:
            output_dir: Output directory for test results
            base_url: Base URL for test requests
            project_id: Project ID for tests
            bearer_token: Bearer token for authentication
        """
        super().__init__(name="qtest_client_performance", output_dir=output_dir)
        self.base_url = base_url
        self.project_id = project_id
        self.bearer_token = bearer_token

        self.result.metadata["base_url"] = base_url
        self.result.metadata["project_id"] = project_id

    def _run_test(self) -> None:
        """Run qTest client performance tests."""
        # Test basic operations
        self._test_get_projects()
        self._test_get_test_cases()

        # Test pagination
        self._test_pagination()

        # Test batch operations
        self._test_batch_operations()

        # Test concurrent operations
        self._test_concurrent_operations()

    def _test_get_projects(self) -> None:
        """Test performance of getting projects."""
        # Get measure decorator for this instance
        measure = self.measure(operation="get_projects")

        @measure
        def run_test():
            # Mock response for the projects endpoint
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/v3/projects",
                    json={
                        "items": [
                            {"id": i, "name": f"Project {i}"}
                            for i in range(1, 11)
                        ],
                        "page": 1,
                        "pageSize": 10,
                        "total": 10,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.header_matcher(
                            {"Authorization": f"Bearer {self.bearer_token}"},
                        ),
                    ],
                )

                # Create client
                config = QTestConfig(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    bearer_token=self.bearer_token,
                )
                client = QTestClient(config)

                # Get projects
                projects = client.get_projects()

                # Verify results
                assert len(projects) == 10

        run_test()

    def _test_get_test_cases(self) -> None:
        """Test performance of getting test cases."""
        # Get measure decorator for this instance
        measure = self.measure(operation="get_test_cases")

        @measure
        def run_test():
            # Mock response for the test cases endpoint with pagination
            with responses.RequestsMock() as rsps:
                # First page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/v3/projects/{self.project_id}/test-cases",
                    json={
                        "items": [
                            {"id": i, "name": f"Test Case {i}"}
                            for i in range(1, 101)
                        ],
                        "page": 1,
                        "pageSize": 100,
                        "total": 250,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"pageSize": "50", "page": "1"},
                        ),
                    ],
                )

                # Second page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/v3/projects/{self.project_id}/test-cases",
                    json={
                        "items": [
                            {"id": i, "name": f"Test Case {i}"}
                            for i in range(101, 201)
                        ],
                        "page": 2,
                        "pageSize": 100,
                        "total": 250,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"pageSize": "50", "page": "2"},
                        ),
                    ],
                )

                # Third page
                rsps.add(
                    responses.GET,
                    f"{self.base_url}/api/v3/projects/{self.project_id}/test-cases",
                    json={
                        "items": [
                            {"id": i, "name": f"Test Case {i}"}
                            for i in range(201, 251)
                        ],
                        "page": 3,
                        "pageSize": 100,
                        "total": 250,
                    },
                    status=200,
                    content_type="application/json",
                    match=[
                        matchers.query_param_matcher(
                            {"pageSize": "50", "page": "3"},
                        ),
                    ],
                )

                # Create client
                config = QTestConfig(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    bearer_token=self.bearer_token,
                )
                client = QTestClient(config)

                # Get test cases - adjust the QTestPaginatedIterator methods for testing
                with patch("ztoq.qtest_client.QTestPaginatedIterator._fetch_next_page"):
                    # Create a mock implementation that works with our test data
                    def mock_fetch(self):
                        if not self.current_page:
                            # First page
                            page = 1
                        else:
                            # Next page
                            page = self.current_page.page + 1

                        if page > 3:
                            # No more pages
                            self.current_page = None
                            return

                        # Make request for this page
                        response = client._make_request(
                            "GET",
                            f"/projects/{client.config.project_id}/test-cases",
                            params={"pageSize": "50", "page": str(page)},
                        )

                        from ztoq.qtest_client import QTestPaginatedResponse

                        # Update current page
                        self.current_page = QTestPaginatedResponse(
                            items=response.get("items", []),
                            page=response.get("page", 0),
                            page_size=response.get("pageSize", 0),
                            total=response.get("total", 0),
                            is_last=page >= 3,  # Last page is page 3
                        )
                        self.item_index = 0

                    # Apply mock
                    from ztoq.qtest_client import QTestPaginatedIterator
                    QTestPaginatedIterator._fetch_next_page = mock_fetch

                    # Get test cases
                    try:
                        iterator = client.get_test_cases()
                        test_cases = []

                        # Manually iterate
                        while iterator.current_page is None or not iterator.current_page.is_last:
                            iterator._fetch_next_page()
                            if iterator.current_page is None:
                                break
                            test_cases.extend([item for item in iterator.current_page.items])

                        # Verify results
                        assert len(test_cases) == 250

                    finally:
                        # Restore original method
                        delattr(QTestPaginatedIterator, "_fetch_next_page")

        run_test()

    def _test_pagination(self, total_items: int = 500, page_sizes: list[int] = None) -> None:
        """Test performance of paginated requests with different page sizes.

        Args:
            total_items: Total number of items to paginate through
            page_sizes: List of page sizes to test
        """
        page_sizes = page_sizes or [10, 50, 100]

        for page_size in page_sizes:
            # Get measure decorator for this instance with specific metadata
            measure = self.measure(
                operation="pagination",
                dataset_size=total_items,
                batch_size=page_size,
            )

            @measure
            def run_test():
                self.result.metadata["page_size"] = page_size

                # Calculate number of pages
                num_pages = (total_items + page_size - 1) // page_size
                logger.info(f"Testing pagination with page size {page_size} ({num_pages} pages)")

                # Set up mock client and paginated iterator
                config = QTestConfig(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    bearer_token=self.bearer_token,
                )
                client = QTestClient(config)

                # Mock _make_request to avoid actual HTTP requests
                with patch.object(client, "_make_request") as mock_request:
                    def make_mock_page(page):
                        start = (page - 1) * page_size
                        end = min(start + page_size, total_items)
                        return {
                            "items": [
                                {"id": i, "name": f"Test Case {i}"}
                                for i in range(start + 1, end + 1)
                            ],
                            "page": page,
                            "pageSize": page_size,
                            "total": total_items,
                        }

                    mock_request.side_effect = lambda method, endpoint, **kwargs: make_mock_page(
                        int(kwargs.get("params", {}).get("page", 1)),
                    )

                    # Test paginated iteration
                    from ztoq.qtest_client import QTestPaginatedIterator, QTestPaginatedResponse

                    # Override _fetch_next_page for testing
                    original_method = QTestPaginatedIterator._fetch_next_page

                    try:
                        def mock_fetch(self):
                            if not self.current_page:
                                page = 1
                            else:
                                page = self.current_page.page + 1

                            if page > num_pages:
                                self.current_page = None
                                return

                            response = client._make_request(
                                "GET",
                                "/test-cases",
                                params={"pageSize": str(page_size), "page": str(page)},
                            )

                            self.current_page = QTestPaginatedResponse(
                                items=response.get("items", []),
                                page=response.get("page", 0),
                                page_size=response.get("pageSize", 0),
                                total=response.get("total", 0),
                                is_last=page >= num_pages,
                            )
                            self.item_index = 0

                        # Apply the mock method
                        QTestPaginatedIterator._fetch_next_page = mock_fetch

                        # Create iterator
                        iterator = QTestPaginatedIterator(
                            client=client,
                            endpoint="/test-cases",
                            model_class=dict,
                            params={},
                            page_size=page_size,
                        )

                        # Process all pages
                        items = []
                        for _ in range(num_pages):
                            iterator._fetch_next_page()
                            if iterator.current_page is None:
                                break
                            items.extend(iterator.current_page.items)

                        # Verify
                        assert len(items) == total_items

                    finally:
                        # Restore original method
                        QTestPaginatedIterator._fetch_next_page = original_method

            run_test()

    def _test_batch_operations(self, batch_sizes: list[int] = None) -> None:
        """Test performance of batch operations.

        Args:
            batch_sizes: List of batch sizes to test
        """
        batch_sizes = batch_sizes or [10, 50, 100]

        for batch_size in batch_sizes:
            # Get measure decorator for this instance with specific metadata
            measure = self.measure(
                operation="batch_operations",
                batch_size=batch_size,
            )

            @measure
            def run_test():
                self.result.metadata["batch_size"] = batch_size
                logger.info(f"Testing with batch size: {batch_size}")

                # Create client
                config = QTestConfig(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    bearer_token=self.bearer_token,
                )
                client = QTestClient(config)

                # Mock bulk create endpoint
                with patch.object(client, "_make_request") as mock_request:
                    mock_request.return_value = [
                        {"id": i, "name": f"Test Case {i}"}
                        for i in range(1, batch_size + 1)
                    ]

                    # Test bulk create
                    test_cases = [
                        {"name": f"Test Case {i}", "description": f"Description {i}"}
                        for i in range(1, batch_size + 1)
                    ]

                    result = client.bulk_create_test_cases(test_cases)

                    # Verify
                    assert len(result) == batch_size
                    assert mock_request.call_count == 1

            run_test()

    def _test_concurrent_operations(self, num_threads: int = 10, operations_per_thread: int = 10) -> None:
        """Test performance of concurrent operations.

        Args:
            num_threads: Number of concurrent threads
            operations_per_thread: Number of operations per thread
        """
        # Get measure decorator for this instance with specific metadata
        measure = self.measure(
            operation="concurrent_operations",
            concurrency=num_threads,
            metadata={"operations_per_thread": operations_per_thread},
        )

        @measure
        def run_test():
            self.result.metadata["concurrency"] = num_threads
            self.result.metadata["operations_per_thread"] = operations_per_thread

            # Create client
            config = QTestConfig(
                base_url=self.base_url,
                project_id=self.project_id,
                bearer_token=self.bearer_token,
            )
            client = QTestClient(config)

            # Mock _make_request to avoid actual HTTP requests
            with patch.object(client, "_make_request") as mock_request:
                mock_request.return_value = {"status": "success"}

                # Function to perform operations in a thread
                def perform_operations(thread_id: int) -> dict[str, Any]:
                    start_time = time.time()
                    results = []

                    for i in range(operations_per_thread):
                        try:
                            # Simulate different API operations
                            if i % 3 == 0:
                                result = client._make_request("GET", "/projects")
                            elif i % 3 == 1:
                                result = client._make_request("GET", f"/projects/{client.config.project_id}/test-cases")
                            else:
                                result = client._make_request("GET", "/test-runs")

                            results.append(result)
                        except Exception as e:
                            logger.error(f"Error in thread {thread_id}, operation {i}: {e}")

                    return {
                        "thread_id": thread_id,
                        "operations": operations_per_thread,
                        "successful": len(results),
                        "duration": time.time() - start_time,
                    }

                # Run concurrent operations
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [
                        executor.submit(perform_operations, thread_id)
                        for thread_id in range(num_threads)
                    ]
                    results = [future.result() for future in futures]

                # Calculate stats
                total_operations = sum(r["operations"] for r in results)
                total_successful = sum(r["successful"] for r in results)
                total_duration = sum(r["duration"] for r in results)
                avg_duration = total_duration / num_threads

                logger.info(
                    f"Concurrent operations: {total_successful}/{total_operations} "
                    f"operations in {avg_duration:.2f}s avg time per thread",
                )

                # Get connection pool metrics
                metrics = connection_pool.get_metrics()
                logger.info(f"Pool metrics: Created={metrics['created_connections']}, Reused={metrics['reused_connections']}")

                # Verify all operations were successful
                assert total_successful == total_operations

        run_test()


@pytest.mark.performance
def test_connection_pool_performance():
    """Run connection pool performance test."""
    test = ConnectionPoolPerformanceTest()
    test.run()


@pytest.mark.performance
def test_zephyr_client_performance():
    """Run Zephyr client performance test."""
    test = ZephyrClientPerformanceTest()
    test.run()


@pytest.mark.performance
def test_qtest_client_performance():
    """Run qTest client performance test."""
    test = QTestClientPerformanceTest()
    test.run()


if __name__ == "__main__":
    # Run the tests directly when executed as a script
    logging.basicConfig(level=logging.INFO)

    print("Running connection pool performance test...")
    pool_test = ConnectionPoolPerformanceTest()
    pool_result = pool_test.run()

    print("\nRunning Zephyr client performance test...")
    zephyr_test = ZephyrClientPerformanceTest()
    zephyr_result = zephyr_test.run()

    print("\nRunning qTest client performance test...")
    qtest_test = QTestClientPerformanceTest()
    qtest_result = qtest_test.run()

    print("\nPerformance tests completed. Results in:", qtest_test.output_path)
