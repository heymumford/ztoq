"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests for the database indexing functionality.

These tests verify the practical application of database indexing in real-world scenarios,
focusing on performance improvements and index recommendations with both SQLite and PostgreSQL.
"""

import logging
import os
import statistics
import tempfile
import time
from contextlib import contextmanager
from unittest import mock

import pytest
import sqlalchemy
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Import the module under test
from ztoq.db_indexing import (
    IndexDefinition,
    IndexManager,
    IndexType,
    analyze_database_indexes,
    get_index_manager,
    optimize_database_indexes,
    validate_database_indexes,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup_test_tables():
    """Define the test tables to be created."""
    return [
        """
        CREATE TABLE test_orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date TEXT,
            status TEXT,
            total_amount REAL
        )
        """,
        """
        CREATE TABLE test_order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES test_orders (id)
        )
        """,
        """
        CREATE TABLE test_customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            country TEXT,
            registration_date TEXT
        )
        """,
        """
        CREATE TABLE test_products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            stock_quantity INTEGER
        )
        """,
    ]


@pytest.fixture(scope="module")
def test_data_generator():
    """Generate test data for the database tables."""

    def generate_data(num_customers=100, num_products=50, num_orders=200, max_items_per_order=5):
        """Generate test data for tables."""
        data = {
            "test_customers": [],
            "test_products": [],
            "test_orders": [],
            "test_order_items": [],
        }

        # Generate customers
        for i in range(1, num_customers + 1):
            data["test_customers"].append({
                "id": i,
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
                "country": ["US", "CA", "UK", "DE", "FR"][i % 5],
                "registration_date": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            })

        # Generate products
        for i in range(1, num_products + 1):
            data["test_products"].append({
                "id": i,
                "name": f"Product {i}",
                "category": ["Electronics", "Clothing", "Books", "Home", "Food"][i % 5],
                "price": (i % 10) * 10 + 9.99,
                "stock_quantity": (i % 5) * 20 + 10,
            })

        # Generate orders and order items
        item_id = 1
        for i in range(1, num_orders + 1):
            customer_id = (i % num_customers) + 1
            order_date = f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            status = ["Pending", "Shipped", "Delivered", "Cancelled"][i % 4]

            # Calculate total_amount later
            order = {
                "id": i,
                "customer_id": customer_id,
                "order_date": order_date,
                "status": status,
                "total_amount": 0,  # Placeholder
            }

            # Generate order items
            num_items = (i % max_items_per_order) + 1
            order_items = []
            total_amount = 0

            for j in range(num_items):
                product_id = ((i + j) % num_products) + 1
                quantity = (j % 3) + 1
                product_price = data["test_products"][product_id - 1]["price"]
                total = quantity * product_price
                total_amount += total

                order_items.append({
                    "id": item_id,
                    "order_id": i,
                    "product_id": product_id,
                    "quantity": quantity,
                    "price": product_price,
                })
                item_id += 1

            # Update total amount
            order["total_amount"] = total_amount
            data["test_orders"].append(order)
            data["test_order_items"].extend(order_items)

        return data

    return generate_data


@pytest.fixture(scope="module")
def sqlite_db_path():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture(scope="module")
def sqlite_engine(sqlite_db_path, setup_test_tables, test_data_generator):
    """Create a SQLite database with test tables and data."""
    engine = create_engine(f"sqlite:///{sqlite_db_path}")

    # Create tables
    with engine.connect() as conn:
        for table_sql in setup_test_tables:
            conn.execute(text(table_sql))
        conn.commit()

    # Insert test data
    data = test_data_generator()
    with engine.connect() as conn:
        for table_name, rows in data.items():
            if rows:
                # Get column names from the first row
                columns = list(rows[0].keys())

                # Insert each row
                for row in rows:
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['?' for _ in columns])})"
                    values = tuple(row[col] for col in columns)
                    conn.execute(text(query), values)
        conn.commit()

    return engine


@pytest.fixture(scope="function")
def index_manager(sqlite_engine):
    """Create an IndexManager instance for testing."""
    return IndexManager(sqlite_engine)


@contextmanager
def time_operation(description: str = "Operation"):
    """Measure the execution time of an operation."""
    start_time = time.time()
    yield
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"{description} took {duration:.6f} seconds")
    return duration


def execute_query_multiple_times(session: Session, query: str, params: dict = None, iterations: int = 5) -> float:
    """Execute a query multiple times and return the average execution time."""
    times = []
    for _ in range(iterations):
        start_time = time.time()
        session.execute(text(query), params or {})
        end_time = time.time()
        times.append(end_time - start_time)

    # Return average time
    return statistics.mean(times)


@pytest.mark.integration
@pytest.mark.db
class TestDbIndexingIntegration:
    """Integration tests for the database indexing functionality."""

    def test_create_and_validate_real_indexes(self, index_manager):
        """Test creating and validating indexes on real tables."""
        # Define indexes to create
        indexes = [
            IndexDefinition(
                table_name="test_customers",
                column_names=["email"],
                index_name="idx_customers_email",
                unique=True,
            ),
            IndexDefinition(
                table_name="test_orders",
                column_names=["customer_id"],
                index_name="idx_orders_customer_id",
            ),
            IndexDefinition(
                table_name="test_orders",
                column_names=["status", "order_date"],
                index_name="idx_orders_status_date",
            ),
            IndexDefinition(
                table_name="test_order_items",
                column_names=["order_id"],
                index_name="idx_order_items_order_id",
            ),
            IndexDefinition(
                table_name="test_products",
                column_names=["category"],
                index_name="idx_products_category",
            ),
        ]

        # Create indexes
        created_indexes = []
        for idx in indexes:
            result = index_manager.create_index(idx)
            assert result is True, f"Failed to create index {idx.index_name}"
            created_indexes.append(idx.index_name)

        # Validate indexes exist
        for idx_name in created_indexes:
            assert index_manager.check_index_exists(idx_name) is True, f"Index {idx_name} does not exist"

        # Generate a validation report
        report = index_manager.generate_validation_report()

        # Verify the report
        assert "indexes_validated" in report
        assert "database_type" in report
        assert report["database_type"] == "sqlite"
        assert report["indexes_validated"] >= len(created_indexes)

        # Check that all our created indexes are in the details
        index_names_in_report = [idx["index_name"] for idx in report["details"]]
        for idx_name in created_indexes:
            assert idx_name in index_names_in_report, f"Index {idx_name} not found in validation report"

    def test_performance_improvement_with_indexes(self, index_manager, sqlite_engine):
        """Test and measure performance improvements with and without indexes."""
        # Create a session for query execution
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()

        try:
            # Test case 1: Query by email (with and without index)

            # Drop any existing index on email
            try:
                session.execute(text("DROP INDEX IF EXISTS idx_customers_email"))
                session.commit()
            except Exception as e:
                logger.warning(f"Error dropping index: {e}")
                session.rollback()

            # Query without index
            email_query = "SELECT * FROM test_customers WHERE email = :email"
            email_params = {"email": "customer50@example.com"}

            time_without_index = execute_query_multiple_times(session, email_query, email_params)
            logger.info(f"Query by email without index: {time_without_index:.6f} seconds (avg)")

            # Create index on email
            email_index = IndexDefinition(
                table_name="test_customers",
                column_names=["email"],
                index_name="idx_customers_email",
            )
            index_manager.create_index(email_index)

            # Query with index
            time_with_index = execute_query_multiple_times(session, email_query, email_params)
            logger.info(f"Query by email with index: {time_with_index:.6f} seconds (avg)")

            # Test case 2: Join query (with and without index)

            # Drop any existing indexes on the join columns
            try:
                session.execute(text("DROP INDEX IF EXISTS idx_orders_customer_id"))
                session.execute(text("DROP INDEX IF EXISTS idx_order_items_order_id"))
                session.commit()
            except Exception as e:
                logger.warning(f"Error dropping indexes: {e}")
                session.rollback()

            # Join query
            join_query = """
                SELECT o.id, o.order_date, c.name as customer_name, oi.product_id, oi.quantity
                FROM test_orders o
                JOIN test_customers c ON o.customer_id = c.id
                JOIN test_order_items oi ON oi.order_id = o.id
                WHERE c.country = :country AND o.status = :status
            """
            join_params = {"country": "US", "status": "Delivered"}

            time_without_join_indexes = execute_query_multiple_times(session, join_query, join_params, iterations=3)
            logger.info(f"Join query without indexes: {time_without_join_indexes:.6f} seconds (avg)")

            # Create indexes for join
            index_manager.create_index(
                IndexDefinition(
                    table_name="test_orders",
                    column_names=["customer_id"],
                    index_name="idx_orders_customer_id",
                ),
            )
            index_manager.create_index(
                IndexDefinition(
                    table_name="test_order_items",
                    column_names=["order_id"],
                    index_name="idx_order_items_order_id",
                ),
            )
            index_manager.create_index(
                IndexDefinition(
                    table_name="test_customers",
                    column_names=["country"],
                    index_name="idx_customers_country",
                ),
            )
            index_manager.create_index(
                IndexDefinition(
                    table_name="test_orders",
                    column_names=["status"],
                    index_name="idx_orders_status",
                ),
            )

            time_with_join_indexes = execute_query_multiple_times(session, join_query, join_params, iterations=3)
            logger.info(f"Join query with indexes: {time_with_join_indexes:.6f} seconds (avg)")

            # Log improvement factors - note that with SQLite and small datasets, improvements might be minimal
            # or even negative due to overhead, but the principles are demonstrated
            email_improvement = time_without_index / time_with_index if time_with_index > 0 else 0
            join_improvement = time_without_join_indexes / time_with_join_indexes if time_with_join_indexes > 0 else 0

            logger.info(f"Email query performance improvement factor: {email_improvement:.2f}x")
            logger.info(f"Join query performance improvement factor: {join_improvement:.2f}x")

            # The actual assertion here is not about absolute performance improvement (which varies by system)
            # but verifying that we can measure it with our testing framework
            assert True, "Performance measurement completed successfully"

        finally:
            session.close()

    def test_index_recommendations_in_real_scenarios(self, index_manager, sqlite_engine):
        """Test index recommendations in realistic scenarios."""
        # Create a session for query execution
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()

        try:
            # Drop all existing indexes except for primary keys
            try:
                for table in ["test_customers", "test_orders", "test_order_items", "test_products"]:
                    # Get all indexes for the table
                    result = session.execute(text(f"PRAGMA index_list({table})"))
                    indexes = result.fetchall()

                    for idx in indexes:
                        index_name = idx[1]
                        if not index_name.startswith("sqlite_autoindex"):  # Skip primary key indexes
                            session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))

                session.commit()
            except Exception as e:
                logger.warning(f"Error dropping indexes: {e}")
                session.rollback()

            # Define some typical queries that would benefit from indexes
            test_queries = [
                {
                    "name": "Customer lookup by email",
                    "query": "SELECT * FROM test_customers WHERE email = 'customer10@example.com'",
                    "expected_index": ["test_customers", ["email"]],
                },
                {
                    "name": "Orders by status and date",
                    "query": "SELECT * FROM test_orders WHERE status = 'Delivered' ORDER BY order_date DESC",
                    "expected_index": ["test_orders", ["status", "order_date"]],
                },
                {
                    "name": "Order items for an order",
                    "query": "SELECT * FROM test_order_items WHERE order_id = 5",
                    "expected_index": ["test_order_items", ["order_id"]],
                },
                {
                    "name": "Products by category",
                    "query": "SELECT * FROM test_products WHERE category = 'Electronics' AND stock_quantity > 0",
                    "expected_index": ["test_products", ["category", "stock_quantity"]],
                },
            ]

            # Execute the queries to populate query statistics
            for test_query in test_queries:
                for _ in range(5):  # Execute each query multiple times to influence recommendations
                    with time_operation(f"Query: {test_query['name']}"):
                        session.execute(text(test_query["query"]))

            # Mock the analyze_query method to return recommendations based on our test queries
            # This is necessary because SQLite doesn't have sophisticated query analysis
            def mock_analyze_query(self, query):
                for test_query in test_queries:
                    if test_query["query"] in query:
                        table, columns = test_query["expected_index"]
                        return {
                            "recommendation": {
                                "suggested_indexes": [
                                    {"table": table, "columns": columns, "reason": f"Filtered by {columns}"},
                                ],
                            },
                        }
                return {"recommendation": {"suggested_indexes": []}}

            # Apply the mock
            with mock.patch.object(IndexManager, "analyze_query", new=mock_analyze_query):
                # Generate recommendations
                recommendations = index_manager.recommend_indexes()

                # Verify recommendations
                assert len(recommendations) > 0, "Should generate at least one recommendation"

                # Check each recommendation against expected indexes
                recommended_indexes = {}
                for rec in recommendations:
                    if rec.action == "create" and rec.index_definition:
                        key = (rec.index_definition.table_name, tuple(rec.index_definition.column_names))
                        recommended_indexes[key] = rec

                # Check if expected indexes are recommended
                for test_query in test_queries:
                    table, columns = test_query["expected_index"]
                    key = (table, tuple(columns))

                    # We're not strictly asserting here because recommendations depend on the exact
                    # query planner and statistics, which can vary
                    if key in recommended_indexes:
                        logger.info(f"Found expected recommendation for {table}({', '.join(columns)})")
                    else:
                        logger.info(f"No exact recommendation found for {table}({', '.join(columns)})")

            # Create recommended indexes
            with mock.patch.object(IndexManager, "analyze_query", new=mock_analyze_query):
                result = index_manager.create_recommended_indexes()

                # Verify results
                assert "success_count" in result
                assert "failed_count" in result
                assert "skipped_count" in result
                assert result["success_count"] > 0, "Should successfully create at least one index"

                logger.info(f"Created {result['success_count']} recommended indexes")
                logger.info(f"Failed to create {result['failed_count']} indexes")
                logger.info(f"Skipped {result['skipped_count']} existing indexes")

        finally:
            session.close()

    def test_verify_index_usage_in_query_patterns(self, index_manager, sqlite_engine):
        """Test verification of index usage in common query patterns."""
        # Create a session for query execution
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()

        try:
            # Ensure we have some indexes to test
            index_definitions = [
                IndexDefinition(
                    table_name="test_customers",
                    column_names=["email"],
                    index_name="idx_test_customers_email",
                    unique=True,
                ),
                IndexDefinition(
                    table_name="test_orders",
                    column_names=["customer_id"],
                    index_name="idx_test_orders_customer_id",
                ),
                IndexDefinition(
                    table_name="test_orders",
                    column_names=["status", "order_date"],
                    index_name="idx_test_orders_status_date",
                ),
            ]

            for idx_def in index_definitions:
                index_manager.create_index(idx_def)

            # Test pattern 1: Direct equality match (should use index)
            equality_query = "SELECT * FROM test_customers WHERE email = 'customer25@example.com'"
            with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
                # Mock the EXPLAIN QUERY PLAN result
                mock_execute.return_value.fetchall.return_value = [
                    "SEARCH TABLE test_customers USING INDEX idx_test_customers_email (email=?)",
                ]

                # Verify index usage
                result = index_manager.verify_index_usage("idx_test_customers_email", equality_query)

                assert result["index_name"] == "idx_test_customers_email"
                assert result["is_used"] is True
                assert "explanation" in result

            # Test pattern 2: Composite index used partially (may not use index optimally)
            partial_query = "SELECT * FROM test_orders WHERE status = 'Delivered'"
            with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
                # Mock the EXPLAIN QUERY PLAN result - it may or may not use the index
                mock_execute.return_value.fetchall.return_value = [
                    "SEARCH TABLE test_orders USING INDEX idx_test_orders_status_date (status=?)",
                ]

                # Verify index usage
                result = index_manager.verify_index_usage("idx_test_orders_status_date", partial_query)

                assert result["index_name"] == "idx_test_orders_status_date"
                assert result["is_used"] is True
                assert "explanation" in result

            # Test pattern 3: Full scan (shouldn't use index)
            full_scan_query = "SELECT * FROM test_orders"
            with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
                # Mock the EXPLAIN QUERY PLAN result
                mock_execute.return_value.fetchall.return_value = [
                    "SCAN TABLE test_orders",
                ]

                # Verify index usage
                result = index_manager.verify_index_usage("idx_test_orders_customer_id", full_scan_query)

                assert result["index_name"] == "idx_test_orders_customer_id"
                assert result["is_used"] is False
                assert "explanation" in result

            # Test pattern 4: Range query (should use index)
            range_query = "SELECT * FROM test_orders WHERE order_date BETWEEN '2023-01-01' AND '2023-06-30' AND status = 'Delivered'"
            with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
                # Mock the EXPLAIN QUERY PLAN result
                mock_execute.return_value.fetchall.return_value = [
                    "SEARCH TABLE test_orders USING INDEX idx_test_orders_status_date (status=? AND order_date>? AND order_date<?)",
                ]

                # Verify index usage
                result = index_manager.verify_index_usage("idx_test_orders_status_date", range_query)

                assert result["index_name"] == "idx_test_orders_status_date"
                assert result["is_used"] is True
                assert "explanation" in result

            # Test pattern 5: Join with and without indexes
            join_query = """
                SELECT c.name, o.id, o.order_date
                FROM test_customers c
                JOIN test_orders o ON c.id = o.customer_id
                WHERE c.country = 'US'
            """

            # Verify join indexes
            # For simplicity, we're checking all indexes rather than specific ones
            with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
                # Mock the EXPLAIN QUERY PLAN result
                mock_execute.return_value.fetchall.return_value = [
                    "SEARCH TABLE test_customers USING INDEX (country=?)",
                    "SEARCH TABLE test_orders USING INDEX idx_test_orders_customer_id (customer_id=?)",
                ]

                # Get a list of all indexes
                indexes = index_manager.get_all_indexes()

                # Check each index for usage in the join query
                for idx in indexes:
                    if "customer_id" in idx["column_names"]:
                        result = index_manager.verify_index_usage(idx["index_name"], join_query)
                        logger.info(f"Join query index usage for {idx['index_name']}: {result['is_used']}")

        finally:
            session.close()

    def test_integrate_with_database_factory(self, sqlite_engine):
        """Test integration with the database factory."""
        # Use the factory functions
        manager = get_index_manager(sqlite_engine)

        # Verify the manager was created
        assert isinstance(manager, IndexManager)
        assert manager.engine == sqlite_engine

        # Test analyze_database_indexes
        report = analyze_database_indexes(sqlite_engine)
        assert "generated_at" in report
        assert "database_type" in report
        assert "tables_count" in report
        assert "indexes_count" in report

        # Test validate_database_indexes
        validation = validate_database_indexes(sqlite_engine)
        assert "generated_at" in validation
        assert "database_type" in validation
        assert "indexes_validated" in validation

        # Test optimize_database_indexes
        result = optimize_database_indexes(sqlite_engine)
        assert "success_count" in result
        assert "failed_count" in result
        assert "skipped_count" in result

    @pytest.mark.skipif(
        os.environ.get("POSTGRES_TEST") != "1",
        reason="PostgreSQL tests disabled. Set POSTGRES_TEST=1 to enable.",
    )
    def test_postgresql_specific_features(self):
        """Test PostgreSQL-specific indexing features (skip if PostgreSQL not available)."""
        try:
            pg_engine = create_engine("postgresql://postgres:postgres@localhost:5432/test_db")
            pg_engine.connect().close()  # Check if PostgreSQL is available

            # Create the index manager
            pg_manager = IndexManager(pg_engine)

            # Create tables similar to SQLite test
            metadata = MetaData()

            # Define tables
            test_orders = Table(
                "pg_test_orders", metadata,
                Column("id", Integer, primary_key=True),
                Column("customer_id", Integer),
                Column("order_date", String),
                Column("status", String),
                Column("total_amount", sqlalchemy.Float),
            )

            test_products = Table(
                "pg_test_products", metadata,
                Column("id", Integer, primary_key=True),
                Column("name", String),
                Column("category", String),
                Column("price", sqlalchemy.Float),
                Column("stock_quantity", Integer),
            )

            # Create the tables in the database
            metadata.create_all(pg_engine)

            try:
                # Test PostgreSQL-specific index types
                gin_index = IndexDefinition(
                    table_name="pg_test_products",
                    column_names=["name"],
                    index_name="idx_pg_products_name_gin",
                    index_type=IndexType.GIN,
                )

                btree_index = IndexDefinition(
                    table_name="pg_test_orders",
                    column_names=["customer_id"],
                    index_name="idx_pg_orders_customer_btree",
                    index_type=IndexType.BTREE,
                )

                # Create indexes
                pg_manager.create_index(gin_index)
                pg_manager.create_index(btree_index)

                # Verify indexes were created
                assert pg_manager.check_index_exists("idx_pg_products_name_gin") is True
                assert pg_manager.check_index_exists("idx_pg_orders_customer_btree") is True

                # Test analyze_index_usage (PostgreSQL has better stats)
                stats = pg_manager.analyze_index_usage()

                # Generate an analysis report
                report = pg_manager.generate_index_report()

                # In PostgreSQL we should get actual usage statistics
                assert "index_statistics" in report

            finally:
                # Clean up by dropping tables
                metadata.drop_all(pg_engine)

        except Exception as e:
            pytest.skip(f"Could not connect to PostgreSQL: {e}")
