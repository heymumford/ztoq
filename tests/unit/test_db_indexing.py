"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the db_indexing module.

These tests verify the functionality of the IndexManager class and related utilities
for creating, analyzing, and optimizing database indexes.
"""

from unittest import mock

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from ztoq.db_indexing import (
    IndexAnalysis,
    IndexDefinition,
    IndexManager,
    IndexRecommendation,
    IndexType,
    analyze_database_indexes,
    get_index_manager,
    optimize_database_indexes,
    validate_database_indexes,
)


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Create a test table
    metadata = MetaData()
    users = Table(
        "users", metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("email", String),
        Column("status", String),
    )

    # Create a test table with foreign key
    posts = Table(
        "posts", metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer),
        Column("title", String),
        Column("content", String),
    )

    metadata.create_all(engine)

    return engine


@pytest.fixture
def index_manager(sqlite_engine):
    """Create an IndexManager with a SQLite engine."""
    return IndexManager(sqlite_engine)


@pytest.fixture
def mock_pg_index_stats():
    """Mock PostgreSQL index statistics."""
    return [
        IndexAnalysis(
            index_name="idx_users_email",
            table_name="users",
            column_names=["email"],
            index_type="btree",
            size_bytes=16384,
            usage_count=150,
            is_effective=True,
            notes="High usage index",
        ),
        IndexAnalysis(
            index_name="idx_users_status",
            table_name="users",
            column_names=["status"],
            index_type="btree",
            size_bytes=8192,
            usage_count=5,
            is_effective=False,
            notes="Low usage index",
        ),
    ]


@pytest.fixture
def mock_index_recommendations():
    """Mock index recommendations."""
    return [
        IndexRecommendation(
            action="create",
            index_definition=IndexDefinition(
                table_name="users",
                column_names=["name"],
                index_name="idx_users_name",
            ),
            rationale="Frequently queried column",
            priority="high",
        ),
        IndexRecommendation(
            action="remove",
            existing_index_name="idx_users_status",
            rationale="Rarely used index",
            priority="medium",
        ),
    ]


class TestIndexManager:
    """Tests for the IndexManager class."""

    def test_init(self, sqlite_engine):
        """Test initialization of IndexManager."""
        manager = IndexManager(sqlite_engine)
        assert manager.engine == sqlite_engine
        assert manager.dialect == "sqlite"

    def test_create_index(self, index_manager):
        """Test creating an index."""
        index_def = IndexDefinition(
            table_name="users",
            column_names=["email"],
            index_name="idx_users_email",
        )

        result = index_manager.create_index(index_def)
        assert result is True

        # Verify the index exists
        assert index_manager.check_index_exists("idx_users_email", "users") is True

    def test_create_index_with_error(self, index_manager):
        """Test error handling when creating an index."""
        # Invalid table name should fail
        index_def = IndexDefinition(
            table_name="nonexistent_table",
            column_names=["email"],
            index_name="idx_nonexistent_email",
        )

        result = index_manager.create_index(index_def)
        assert result is False

    def test_remove_index(self, index_manager):
        """Test removing an index."""
        # First create an index
        index_def = IndexDefinition(
            table_name="users",
            column_names=["email"],
            index_name="idx_users_email",
        )
        index_manager.create_index(index_def)

        # Now remove it
        result = index_manager.remove_index("idx_users_email", "users")
        assert result is True

        # Verify the index no longer exists
        assert index_manager.check_index_exists("idx_users_email", "users") is False

    def test_check_index_exists(self, index_manager):
        """Test checking if an index exists."""
        # Create an index first
        index_def = IndexDefinition(
            table_name="users",
            column_names=["email"],
            index_name="idx_users_email",
        )
        index_manager.create_index(index_def)

        # Test with correct table
        assert index_manager.check_index_exists("idx_users_email", "users") is True

        # Test with no table specified
        assert index_manager.check_index_exists("idx_users_email") is True

        # Test with non-existent index
        assert index_manager.check_index_exists("idx_nonexistent") is False

    @mock.patch("ztoq.db_indexing.IndexManager.analyze_index_usage")
    def test_generate_index_report(self, mock_analyze, index_manager, mock_pg_index_stats, mock_index_recommendations):
        """Test generating an index report."""
        # Mock the analyze_index_usage method
        mock_analyze.return_value = mock_pg_index_stats

        # Mock the recommend_indexes method
        with mock.patch.object(index_manager, "recommend_indexes", return_value=mock_index_recommendations):
            # Mock the _get_table_statistics method
            with mock.patch.object(index_manager, "_get_table_statistics", return_value=[
                {"table_name": "users", "row_count": 1000, "column_count": 4, "size_bytes": 32768},
            ]):
                report = index_manager.generate_index_report()

                # Verify report structure
                assert "generated_at" in report
                assert "database_type" in report
                assert "tables_count" in report
                assert "indexes_count" in report
                assert "table_statistics" in report
                assert "index_statistics" in report
                assert "recommendations" in report
                assert "summary" in report

                # Verify report content
                assert report["database_type"] == "sqlite"
                assert report["tables_count"] == 1
                assert report["indexes_count"] == 2
                assert len(report["table_statistics"]) == 1
                assert len(report["index_statistics"]) == 2
                assert len(report["recommendations"]) == 2

    @mock.patch("ztoq.db_indexing.IndexManager.analyze_query")
    def test_recommend_indexes(self, mock_analyze_query, index_manager):
        """Test recommending indexes."""
        # Mock analyze_index_usage to return some unused indexes
        with mock.patch.object(index_manager, "analyze_index_usage", return_value=[
            IndexAnalysis(
                index_name="idx_users_status",
                table_name="users",
                column_names=["status"],
                index_type="btree",
                is_effective=False,
            ),
        ]):
            # Mock _get_slow_queries to return a slow query
            with mock.patch.object(index_manager, "_get_slow_queries", return_value=[
                {"query": "SELECT * FROM users WHERE name = 'test'", "count": 100},
            ]):
                # Mock analyze_query to return a recommendation
                mock_analyze_query.return_value = {
                    "recommendation": {
                        "suggested_indexes": [
                            {"table": "users", "columns": ["name"], "reason": "Equality filter on name"},
                        ],
                    },
                }

                # Mock _recommend_indexes_for_foreign_keys
                with mock.patch.object(index_manager, "_recommend_indexes_for_foreign_keys", return_value=[
                    IndexRecommendation(
                        action="create",
                        index_definition=IndexDefinition(
                            table_name="posts",
                            column_names=["user_id"],
                            index_name="idx_posts_user_id",
                        ),
                        rationale="Foreign key to users (id) is not indexed",
                        priority="high",
                    ),
                ]):
                    recommendations = index_manager.recommend_indexes()

                    # Should have recommendations to remove unused index and create two new indexes
                    assert len(recommendations) == 3

                    # Check for the specific recommendations
                    actions = [rec.action for rec in recommendations]
                    assert "remove" in actions
                    assert "create" in actions

                    # Check for specific tables and columns
                    for rec in recommendations:
                        if rec.action == "create" and rec.index_definition:
                            if rec.index_definition.table_name == "users":
                                assert rec.index_definition.column_names == ["name"]
                            elif rec.index_definition.table_name == "posts":
                                assert rec.index_definition.column_names == ["user_id"]

    def test_verify_index_usage_sqlite(self, index_manager):
        """Test verifying index usage in SQLite."""
        # Create an index to test
        index_def = IndexDefinition(
            table_name="users",
            column_names=["email"],
            index_name="idx_users_email",
        )
        index_manager.create_index(index_def)

        # Use a mocked execute return value for the EXPLAIN QUERY PLAN
        with mock.patch("sqlalchemy.engine.Connection.execute") as mock_execute:
            # Mock the EXPLAIN QUERY PLAN result to indicate index usage
            mock_execute.return_value.fetchall.return_value = [
                "SEARCH TABLE users USING INDEX idx_users_email (email=?)",
            ]

            # Test a query that should use the index
            result = index_manager.verify_index_usage("idx_users_email", "SELECT * FROM users WHERE email = 'test@example.com'")

            assert result["index_name"] == "idx_users_email"
            assert result["is_used"] is True
            assert "explanation" in result

    def test_get_recommended_indexes(self, index_manager):
        """Test getting recommended indexes."""
        indexes = index_manager.get_recommended_indexes()

        # Verify we have recommendations
        assert len(indexes) > 0

        # Check structure of recommendations
        for idx in indexes:
            assert isinstance(idx, IndexDefinition)
            assert idx.table_name
            assert len(idx.column_names) > 0
            assert idx.index_name

    @mock.patch("ztoq.db_indexing.IndexManager.create_index")
    @mock.patch("ztoq.db_indexing.IndexManager.check_index_exists")
    def test_create_recommended_indexes(self, mock_check_exists, mock_create, index_manager):
        """Test creating recommended indexes."""
        # Mock to return some indexes that exist and some that don't
        mock_check_exists.side_effect = [True, False, False]

        # Mock create_index to succeed for the first and fail for the second
        mock_create.side_effect = [True, False]

        # Mock get_recommended_indexes to return 3 indexes
        with mock.patch.object(index_manager, "get_recommended_indexes", return_value=[
            IndexDefinition(
                table_name="users",
                column_names=["email"],
                index_name="idx_users_email",
            ),
            IndexDefinition(
                table_name="users",
                column_names=["name"],
                index_name="idx_users_name",
            ),
            IndexDefinition(
                table_name="posts",
                column_names=["title"],
                index_name="idx_posts_title",
            ),
        ]):
            result = index_manager.create_recommended_indexes()

            # Verify the result counts
            assert result["skipped_count"] == 1
            assert result["success_count"] == 1
            assert result["failed_count"] == 1
            assert len(result["details"]) == 3

    @mock.patch("ztoq.db_indexing.IndexManager.analyze_index_usage")
    def test_generate_validation_report(self, mock_analyze, index_manager, mock_pg_index_stats):
        """Test generating a validation report."""
        # Mock analyze_index_usage
        mock_analyze.return_value = mock_pg_index_stats

        report = index_manager.generate_validation_report()

        # Verify report structure
        assert "generated_at" in report
        assert "database_type" in report
        assert "indexes_validated" in report
        assert "indexes_used" in report
        assert "indexes_unused" in report
        assert "details" in report

        # Verify counts
        assert report["indexes_validated"] == 2
        assert report["indexes_used"] == 1
        assert report["indexes_unused"] == 1
        assert len(report["details"]) == 2


class TestUtilityFunctions:
    """Tests for utility functions in the db_indexing module."""

    def test_get_index_manager(self, sqlite_engine):
        """Test getting an index manager."""
        # Test with engine
        manager = get_index_manager(sqlite_engine)
        assert isinstance(manager, IndexManager)
        assert manager.engine == sqlite_engine

        # Test with connection URL
        with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_create_engine.return_value = sqlite_engine
            manager = get_index_manager("sqlite:///:memory:")
            assert isinstance(manager, IndexManager)
            mock_create_engine.assert_called_once_with("sqlite:///:memory:")

    @mock.patch("ztoq.db_indexing.get_index_manager")
    def test_optimize_database_indexes(self, mock_get_manager, index_manager):
        """Test optimizing database indexes."""
        # Mock the get_index_manager function
        mock_get_manager.return_value = index_manager

        # Mock the create_recommended_indexes method
        expected_result = {"success_count": 2, "failed_count": 1, "skipped_count": 0}
        with mock.patch.object(index_manager, "create_recommended_indexes", return_value=expected_result):
            result = optimize_database_indexes("sqlite:///:memory:")
            assert result == expected_result
            mock_get_manager.assert_called_once_with("sqlite:///:memory:")

    @mock.patch("ztoq.db_indexing.get_index_manager")
    def test_analyze_database_indexes(self, mock_get_manager, index_manager):
        """Test analyzing database indexes."""
        # Mock the get_index_manager function
        mock_get_manager.return_value = index_manager

        # Mock the generate_index_report method
        expected_result = {"generated_at": "2025-04-24T12:00:00"}
        with mock.patch.object(index_manager, "generate_index_report", return_value=expected_result):
            result = analyze_database_indexes("sqlite:///:memory:")
            assert result == expected_result
            mock_get_manager.assert_called_once_with("sqlite:///:memory:")

    @mock.patch("ztoq.db_indexing.get_index_manager")
    def test_validate_database_indexes(self, mock_get_manager, index_manager):
        """Test validating database indexes."""
        # Mock the get_index_manager function
        mock_get_manager.return_value = index_manager

        # Mock the generate_validation_report method
        expected_result = {"generated_at": "2025-04-24T12:00:00"}
        with mock.patch.object(index_manager, "generate_validation_report", return_value=expected_result):
            result = validate_database_indexes("sqlite:///:memory:")
            assert result == expected_result
            mock_get_manager.assert_called_once_with("sqlite:///:memory:")


class TestIndexDefinition:
    """Tests for the IndexDefinition class."""

    def test_init(self):
        """Test initialization of IndexDefinition."""
        # Test with provided index name
        idx = IndexDefinition(
            table_name="users",
            column_names=["email"],
            index_name="idx_users_email",
        )
        assert idx.table_name == "users"
        assert idx.column_names == ["email"]
        assert idx.index_name == "idx_users_email"
        assert idx.index_type == IndexType.BTREE
        assert idx.unique is False

        # Test auto-generated index name
        idx = IndexDefinition(
            table_name="users",
            column_names=["email", "status"],
        )
        assert idx.index_name == "idx_users_email_status"

        # Test very long index name gets hashed
        idx = IndexDefinition(
            table_name="very_long_table_name_that_would_exceed_the_limit",
            column_names=["very_long_column_name_that_would_exceed_the_limit", "another_long_column"],
        )
        assert len(idx.index_name) < 64  # Ensure it's not too long

        # Test unique index
        idx = IndexDefinition(
            table_name="users",
            column_names=["email"],
            unique=True,
        )
        assert idx.index_name.startswith("unq_")
        assert idx.unique is True


class TestIndexType:
    """Tests for the IndexType enum."""

    def test_index_types(self):
        """Test index type values."""
        assert IndexType.BTREE.value == "btree"
        assert IndexType.HASH.value == "hash"
        assert IndexType.GIN.value == "gin"
        assert IndexType.GIST.value == "gist"
        assert IndexType.BRIN.value == "brin"
        assert IndexType.UNIQUE.value == "unique"
        assert IndexType.PRIMARY.value == "primary"
