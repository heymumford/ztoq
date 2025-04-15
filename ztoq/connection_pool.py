"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Connection pooling module for HTTP clients.

This module provides connection pooling for HTTP clients to improve performance
with high-volume API calls. It includes both synchronous (using requests.Session)
and asynchronous (using aiohttp/httpx) implementations.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ConnectionError, HTTPError, RequestException, RetryError, Timeout

# Optional async imports for async client
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Configure module logger
logger = logging.getLogger("ztoq.connection_pool")


class ConnectionPool:
    """
    Connection pool for HTTP clients using requests.Session.

    This class manages connection pools for different base URLs, with automatic
    connection reuse, retry mechanisms, and connection cleanup.

    Attributes:
        pools: Dictionary mapping base URLs to session pools
        max_pool_size: Maximum number of sessions per pool
        connection_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        max_retries: Maximum number of retries for failed requests
        retry_backoff_factor: Backoff factor for retries
        retry_status_codes: HTTP status codes to retry on
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConnectionPool, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self,
                 max_pool_size: int = 10,
                 connection_timeout: float = 5.0,
                 read_timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_backoff_factor: float = 0.5,
                 retry_status_codes: List[int] = None):
        """
        Initialize the connection pool manager.

        Args:
            max_pool_size: Maximum number of connections per base URL pool
            connection_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_backoff_factor: Backoff factor for retries
            retry_status_codes: HTTP status codes to retry on (defaults to [429, 500, 502, 503, 504])
        """
        # Initialize only once (singleton pattern)
        with self._lock:
            if self._initialized:
                return

            # Set environment variable to enable keep-alive for requests
            os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"

            self.pools = {}
            self.max_pool_size = max_pool_size
            self.connection_timeout = connection_timeout
            self.read_timeout = read_timeout
            self.max_retries = max_retries
            self.retry_backoff_factor = retry_backoff_factor

            # Default retry status codes if none provided
            if retry_status_codes is None:
                retry_status_codes = [429, 500, 502, 503, 504]
            self.retry_status_codes = retry_status_codes

            # Heartbeat to clean up idle connections
            self._last_cleanup = time.time()
            self._cleanup_interval = 60  # seconds

            # Pool metrics
            self.metrics = {
                "created_connections": 0,
                "reused_connections": 0,
                "failed_connections": 0,
                "active_pools": 0,
                "last_cleanup": 0
            }

            self._initialized = True
            logger.debug(f"ConnectionPool initialized with max_pool_size={max_pool_size}")

    def _get_base_url(self, url: str) -> str:
        """
        Extract the base URL (scheme + netloc) from a URL.

        Args:
            url: The full URL

        Returns:
            The base URL (scheme + netloc)
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _create_session(self) -> requests.Session:
        """
        Create a new session with retry configuration.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_backoff_factor,
            status_forcelist=self.retry_status_codes,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            raise_on_redirect=False,
            raise_on_status=False
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.max_pool_size,
            pool_maxsize=self.max_pool_size
        )

        # Mount the adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_pool(self, base_url: str) -> List[requests.Session]:
        """
        Get or create a session pool for a base URL.

        Args:
            base_url: The base URL to create a pool for

        Returns:
            List of session objects for the pool
        """
        with self._lock:
            if base_url not in self.pools:
                self.pools[base_url] = []
                self.metrics["active_pools"] = len(self.pools)
                logger.debug(f"Created new pool for {base_url}")

            return self.pools[base_url]

    @contextmanager
    def get_session(self, url: str) -> requests.Session:
        """
        Get a session from the pool or create a new one.

        This is a context manager that handles returning the session to the pool
        after use.

        Args:
            url: The URL to get a session for

        Yields:
            A session object
        """
        base_url = self._get_base_url(url)
        pool = self._get_pool(base_url)
        session = None

        try:
            # Try to get a session from the pool
            with self._lock:
                if pool:
                    session = pool.pop()
                    self.metrics["reused_connections"] += 1
                    logger.debug(f"Reused connection from pool for {base_url}")
                else:
                    # Create a new session if the pool is empty
                    session = self._create_session()
                    self.metrics["created_connections"] += 1
                    logger.debug(f"Created new connection for {base_url}")

            # Perform cleanup if needed (not inside lock to avoid blocking)
            self._maybe_cleanup()

            # Yield the session for use
            yield session

        except Exception as e:
            self.metrics["failed_connections"] += 1
            logger.error(f"Connection error for {base_url}: {e}")
            # If the session is broken, don't return it to the pool
            session = None
            raise

        finally:
            # Return the session to the pool if it's still valid
            if session is not None:
                with self._lock:
                    if len(pool) < self.max_pool_size:
                        pool.append(session)
                    else:
                        # Pool is full, close the session
                        try:
                            session.close()
                        except Exception as e:
                            logger.warning(f"Error closing session: {e}")

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make a request using a pooled session.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments for requests.request

        Returns:
            requests.Response object

        Raises:
            HTTPError: If the HTTP request failed
            ConnectionError: If there was a connection error
            Timeout: If the request timed out
            RequestException: For any other request error
        """
        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connection_timeout, self.read_timeout)

        # Get a session from the pool
        with self.get_session(url) as session:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    def _maybe_cleanup(self):
        """Periodically clean up idle connections."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            threading.Thread(target=self._cleanup_idle_connections).start()
            self._last_cleanup = current_time

    def _cleanup_idle_connections(self):
        """Clean up idle connections in all pools."""
        with self._lock:
            before_count = sum(len(pool) for pool in self.pools.values())

            # Clear idle connections from pools
            for base_url, pool in list(self.pools.items()):
                # Close and recreate each session to ensure connections are properly closed
                for session in pool:
                    try:
                        session.close()
                    except Exception as e:
                        logger.warning(f"Error closing session during cleanup: {e}")

                # Reset the pool
                self.pools[base_url] = []

                # Remove empty pools
                if not pool:
                    del self.pools[base_url]

            after_count = sum(len(pool) for pool in self.pools.values())

            # Update metrics
            self.metrics["active_pools"] = len(self.pools)
            self.metrics["last_cleanup"] = time.time()

            logger.debug(f"Cleaned up connection pools: {before_count} -> {after_count} connections")

    def close_all(self):
        """Close all connections in all pools."""
        with self._lock:
            for base_url, pool in list(self.pools.items()):
                for session in pool:
                    try:
                        session.close()
                    except Exception as e:
                        logger.warning(f"Error closing session during shutdown: {e}")

                self.pools[base_url] = []

            self.pools = {}
            self.metrics["active_pools"] = 0
            logger.info("All connection pools closed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about pool usage."""
        with self._lock:
            metrics = self.metrics.copy()
            # Return the actual pool size for each URL for test compatibility
            metrics["pools"] = {url: pool for url, pool in self.pools.items()}
            return metrics


class AsyncConnectionPool:
    """
    Asynchronous connection pool for HTTP clients.

    This class provides connection pooling for asynchronous HTTP clients using
    either httpx (preferred) or aiohttp. It's designed to work with asyncio.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncConnectionPool, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self,
                 max_connections: int = 100,
                 connection_timeout: float = 5.0,
                 read_timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_backoff_factor: float = 0.5,
                 retry_status_codes: List[int] = None):
        """
        Initialize the async connection pool.

        Args:
            max_connections: Maximum number of connections to maintain in the pool
            connection_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_backoff_factor: Backoff factor for retries
            retry_status_codes: HTTP status codes to retry on
        """
        with self._lock:
            if self._initialized:
                return

            # Check for available async HTTP libraries
            if not HTTPX_AVAILABLE and not AIOHTTP_AVAILABLE:
                raise ImportError(
                    "Either httpx or aiohttp must be installed for async connection pooling. "
                    "Install with: pip install httpx or pip install aiohttp"
                )

            self.max_connections = max_connections
            self.connection_timeout = connection_timeout
            self.read_timeout = read_timeout
            self.max_retries = max_retries
            self.retry_backoff_factor = retry_backoff_factor

            # Default retry status codes if none provided
            if retry_status_codes is None:
                retry_status_codes = [429, 500, 502, 503, 504]
            self.retry_status_codes = retry_status_codes

            # Track clients
            self.clients = {}

            # Metrics
            self.metrics = {
                "created_clients": 0,
                "reused_clients": 0,
                "active_clients": 0,
            }

            # Determine which async HTTP client to use
            self.client_type = "httpx" if HTTPX_AVAILABLE else "aiohttp"
            logger.debug(f"Using {self.client_type} for async connection pooling")

            self._initialized = True
            logger.debug(f"AsyncConnectionPool initialized with max_connections={max_connections}")

    def create_client(self, base_url: str = None):
        """
        Create a new async HTTP client with the appropriate configuration.

        Args:
            base_url: Optional base URL for the client

        Returns:
            An async HTTP client (httpx.AsyncClient or aiohttp.ClientSession)
        """
        if self.client_type == "httpx":
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_connections
            )

            timeout = httpx.Timeout(
                connect=self.connection_timeout,
                read=self.read_timeout
            )

            transport = httpx.AsyncHTTPTransport(
                limits=limits,
                retries=self.max_retries
            )

            client = httpx.AsyncClient(
                base_url=base_url,
                timeout=timeout,
                transport=transport,
                follow_redirects=True
            )

        else:  # aiohttp
            timeout = aiohttp.ClientTimeout(
                connect=self.connection_timeout,
                total=self.read_timeout
            )

            client = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    limit=self.max_connections,
                    force_close=False,
                    enable_cleanup_closed=True
                ),
                base_url=base_url
            )

        self.metrics["created_clients"] += 1
        return client

    def get_client(self, base_url: str = None):
        """
        Get or create an async HTTP client for a base URL.

        Args:
            base_url: Optional base URL for the client

        Returns:
            An async HTTP client
        """
        key = base_url or "default"

        with self._lock:
            if key not in self.clients:
                self.clients[key] = self.create_client(base_url)
                self.metrics["active_clients"] = len(self.clients)
                logger.debug(f"Created new async client for {key}")
            else:
                self.metrics["reused_clients"] += 1
                logger.debug(f"Reused async client for {key}")

            return self.clients[key]

    async def close_all(self):
        """Close all async HTTP clients."""
        with self._lock:
            for key, client in list(self.clients.items()):
                try:
                    await client.aclose() if self.client_type == "httpx" else await client.close()
                except Exception as e:
                    logger.warning(f"Error closing async client for {key}: {e}")

            self.clients = {}
            self.metrics["active_clients"] = 0
            logger.info("All async clients closed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about pool usage."""
        with self._lock:
            return self.metrics.copy()


# Create singleton instances
connection_pool = ConnectionPool()
async_connection_pool = None if not (HTTPX_AVAILABLE or AIOHTTP_AVAILABLE) else AsyncConnectionPool()


@contextmanager
def get_session(url: str) -> requests.Session:
    """
    Convenience function to get a session from the default connection pool.

    Args:
        url: The URL to get a session for

    Yields:
        A requests.Session object
    """
    with connection_pool.get_session(url) as session:
        yield session


def make_request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Make a request using the default connection pool.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        **kwargs: Additional arguments for requests.request

    Returns:
        requests.Response object
    """
    return connection_pool.request(method, url, **kwargs)


def close_connection_pools():
    """
    Close all connection pools. Should be called at application shutdown.
    """
    connection_pool.close_all()
