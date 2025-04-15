"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database indexing utilities for ZTOQ.

This module provides functionality for creating, managing, and verifying database indexes
in both SQLite and PostgreSQL databases to optimize query performance as part of PERF-6.
It includes tools for automatic index recommendations based on query analysis and
validation of index usage.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Index, MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Types of database indexes."""

    BTREE = "btree"     # Standard B-tree index
    HASH = "hash"       # Hash index (PostgreSQL only)
    GIN = "gin"         # Generalized Inverted Index (PostgreSQL only, for JSON/arrays)
    GIST = "gist"       # Generalized Search Tree (PostgreSQL only)
    BRIN = "brin"       # Block Range Index (PostgreSQL only, for large tables)
    UNIQUE = "unique"   # Unique constraint index
    PRIMARY = "primary" # Primary key index


@dataclass
class IndexDefinition:
    """Definition of a database index."""

    table_name: str
    column_names: list[str]
    index_name: str | None = None
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    condition: str | None = None  # For partial indexes (WHERE clause)

    def __post_init__(self):
        """Generate index name if not provided."""
        if not self.index_name:
            col_str = "_".join(self.column_names)
            index_type = "unq" if self.unique else "idx"
            self.index_name = f"{index_type}_{self.table_name}_{col_str}"

            # Ensure name isn't too long for some database systems
            if len(self.index_name) > 63:
                self.index_name = f"{index_type}_{self.table_name}_{hash(col_str) % 10000}"


@dataclass
class IndexAnalysis:
    """Analysis results for a database index."""

    index_name: str
    table_name: str
    column_names: list[str]
    index_type: str
    size_bytes: int | None = None
    usage_count: int | None = None
    last_used: datetime | None = None
    is_effective: bool | None = None
    notes: str | None = None


@dataclass
class QueryAnalysisEntry:
    """Entry for query analysis with performance metrics."""

    query_text: str
    execution_count: int
    avg_execution_time: float
    tables_accessed: list[str]
    columns_accessed: dict[str, list[str]]
    scan_type: str  # e.g., "FULL TABLE SCAN", "INDEX SCAN"
    index_used: str | None = None


@dataclass
class IndexRecommendation:
    """Recommendation for index creation or removal."""

    action: str  # "create", "remove", "modify"
    index_definition: IndexDefinition | None = None
    existing_index_name: str | None = None
    rationale: str | None = None
    estimated_impact: str | None = None
    priority: str = "medium"  # "high", "medium", "low"


class IndexManager:
    """
    Manages database indexes for both SQLite and PostgreSQL databases.
    
    This class provides methods for creating, listing, analyzing, and 
    removing indexes, as well as generating recommendations for index
    optimization.
    """

    def __init__(self, engine: Engine):
        """
        Initialize the index manager.
        
        Args:
            engine: SQLAlchemy engine for database connections

        """
        self.engine = engine
        self.dialect = engine.dialect.name
        self.metadata = MetaData()
        self.metadata.reflect(bind=engine)
        self.session_factory = sessionmaker(bind=engine)

    def get_all_indexes(self) -> dict[str, list[dict[str, Any]]]:
        """
        Get all indexes in the database.
        
        Returns:
            Dictionary mapping table names to lists of index information

        """
        inspector = inspect(self.engine)
        result = {}

        for table_name in inspector.get_table_names():
            indexes = inspector.get_indexes(table_name)
            if indexes:
                result[table_name] = indexes

        return result

    def create_index(self, index_def: IndexDefinition) -> bool:
        """
        Create a database index.
        
        Args:
            index_def: Index definition
            
        Returns:
            True if index was created successfully, False otherwise

        """
        try:
            table = Table(index_def.table_name, self.metadata, autoload_with=self.engine)

            # Build column list
            columns = [getattr(table.c, col_name) for col_name in index_def.column_names]

            # Create the index
            idx = Index(
                index_def.index_name,
                *columns,
                unique=index_def.unique,
                postgresql_using=index_def.index_type.value if self.dialect == "postgresql" else None,
            )

            # Add condition for partial index if provided (PostgreSQL only)
            if index_def.condition and self.dialect == "postgresql":
                idx = idx.dialect_options(postgresql_where=text(index_def.condition))

            # Create the index in the database
            with self.engine.begin() as conn:
                idx.create(conn)

            logger.info(f"Created index {index_def.index_name} on {index_def.table_name}({', '.join(index_def.column_names)})")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_def.index_name}: {e!s}")
            return False

    def remove_index(self, index_name: str, table_name: str) -> bool:
        """
        Remove a database index.
        
        Args:
            index_name: Name of the index to remove
            table_name: Name of the table the index is on
            
        Returns:
            True if index was removed successfully, False otherwise

        """
        try:
            with self.engine.begin() as conn:
                if self.dialect == "postgresql":
                    conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                else:
                    conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))

            logger.info(f"Removed index {index_name} from table {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove index {index_name}: {e!s}")
            return False

    def check_index_exists(self, index_name: str, table_name: str | None = None) -> bool:
        """
        Check if an index exists.
        
        Args:
            index_name: Name of the index to check
            table_name: Optional table name to limit the search
            
        Returns:
            True if index exists, False otherwise

        """
        inspector = inspect(self.engine)

        if table_name:
            # Check only the specified table
            indexes = inspector.get_indexes(table_name)
            return any(idx["name"] == index_name for idx in indexes)
        # Check all tables
        for table in inspector.get_table_names():
            indexes = inspector.get_indexes(table)
            if any(idx["name"] == index_name for idx in indexes):
                return True

        return False

    def analyze_index_usage(self, min_usage_threshold: int = 10) -> list[IndexAnalysis]:
        """
        Analyze index usage and effectiveness.
        
        Args:
            min_usage_threshold: Minimum usage count to consider an index effective
            
        Returns:
            List of index analysis results

        """
        results = []

        with self.session_factory() as session:
            if self.dialect == "postgresql":
                # PostgreSQL provides index usage statistics
                query = text("""
                    SELECT
                        idx.indexrelname AS index_name,
                        t.relname AS table_name,
                        pg_relation_size(idx.indexrelid) AS index_size,
                        idx_scan AS usage_count,
                        idx_tup_read,
                        idx_tup_fetch,
                        indexdef
                    FROM pg_stat_user_indexes AS idx
                    JOIN pg_indexes ON idx.indexrelname = pg_indexes.indexname
                    JOIN pg_class AS t ON idx.relid = t.oid
                    ORDER BY index_size DESC;
                """)

                for row in session.execute(query):
                    # Extract column names from index definition
                    index_def = row.indexdef
                    columns_start = index_def.find("(") + 1
                    columns_end = index_def.rfind(")")
                    columns_str = index_def[columns_start:columns_end]
                    column_names = [col.strip() for col in columns_str.split(",")]

                    # Determine index type
                    index_type = IndexType.BTREE.value
                    if "USING" in index_def:
                        using_idx = index_def.find("USING") + 6
                        using_end = index_def.find(" ", using_idx)
                        index_type = index_def[using_idx:using_end].lower()

                    # Calculate effectiveness
                    is_effective = row.usage_count >= min_usage_threshold

                    analysis = IndexAnalysis(
                        index_name=row.index_name,
                        table_name=row.table_name,
                        column_names=column_names,
                        index_type=index_type,
                        size_bytes=row.index_size,
                        usage_count=row.usage_count,
                        is_effective=is_effective,
                        notes=f"Reads: {row.idx_tup_read}, Fetches: {row.idx_tup_fetch}",
                    )

                    results.append(analysis)

            elif self.dialect == "sqlite":
                # SQLite has limited statistics, use EXPLAIN QUERY PLAN

                # First get all indexes
                all_indexes = self.get_all_indexes()

                # Then collect information about each index
                for table_name, indexes in all_indexes.items():
                    for idx in indexes:
                        # Execute a test query using this index to see if it's used
                        column_names = idx["column_names"]
                        if not column_names:
                            continue

                        # Construct a simple query that should use this index
                        first_column = column_names[0]
                        test_query = f"EXPLAIN QUERY PLAN SELECT * FROM {table_name} WHERE {first_column} = 1"

                        plan_rows = session.execute(text(test_query)).fetchall()
                        plan_text = str(plan_rows)

                        # Check if the plan uses this index
                        index_used = idx["name"] in plan_text or "USING INDEX" in plan_text

                        analysis = IndexAnalysis(
                            index_name=idx["name"],
                            table_name=table_name,
                            column_names=column_names,
                            index_type="btree",  # SQLite primarily uses B-tree indexes
                            usage_count=None,  # SQLite doesn't track usage count
                            is_effective=index_used,
                            notes="Index usability verified via EXPLAIN QUERY PLAN",
                        )

                        results.append(analysis)

        return results

    def generate_index_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive report on database indexes.
        
        Returns:
            Dictionary containing index analysis and recommendations

        """
        # Collect all indexes and their statistics
        index_stats = self.analyze_index_usage()

        # Get table sizes and row counts
        table_stats = self._get_table_statistics()

        # Collect recommendations
        recommendations = self.recommend_indexes()

        # Prepare the report
        report = {
            "generated_at": datetime.now().isoformat(),
            "database_type": self.dialect,
            "tables_count": len(table_stats),
            "indexes_count": len(index_stats),
            "table_statistics": table_stats,
            "index_statistics": [vars(stat) for stat in index_stats],
            "recommendations": [vars(rec) for rec in recommendations],
            "summary": self._generate_summary(index_stats, recommendations),
        }

        return report

    def _get_table_statistics(self) -> list[dict[str, Any]]:
        """
        Get statistics about tables in the database.
        
        Returns:
            List of dictionaries with table statistics

        """
        stats = []
        inspector = inspect(self.engine)

        with self.session_factory() as session:
            for table_name in inspector.get_table_names():
                row_count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                row_count = session.execute(row_count_query).scalar()

                # Get size if PostgreSQL
                size_bytes = None
                if self.dialect == "postgresql":
                    size_query = text(f"SELECT pg_relation_size('{table_name}')")
                    size_bytes = session.execute(size_query).scalar()

                # Get column count
                columns = inspector.get_columns(table_name)

                stats.append({
                    "table_name": table_name,
                    "row_count": row_count,
                    "column_count": len(columns),
                    "size_bytes": size_bytes,
                })

        return stats

    def _generate_summary(self, index_stats: list[IndexAnalysis],
                         recommendations: list[IndexRecommendation]) -> dict[str, Any]:
        """
        Generate a summary of index analysis and recommendations.
        
        Args:
            index_stats: List of index analysis results
            recommendations: List of index recommendations
            
        Returns:
            Dictionary with summary information

        """
        # Count ineffective indexes
        ineffective_count = sum(1 for stat in index_stats if stat.is_effective is False)

        # Group recommendations by priority
        rec_by_priority = {
            "high": sum(1 for rec in recommendations if rec.priority == "high"),
            "medium": sum(1 for rec in recommendations if rec.priority == "medium"),
            "low": sum(1 for rec in recommendations if rec.priority == "low"),
        }

        # Group recommendations by action
        rec_by_action = {
            "create": sum(1 for rec in recommendations if rec.action == "create"),
            "remove": sum(1 for rec in recommendations if rec.action == "remove"),
            "modify": sum(1 for rec in recommendations if rec.action == "modify"),
        }

        return {
            "total_indexes": len(index_stats),
            "ineffective_indexes": ineffective_count,
            "recommendation_count": len(recommendations),
            "recommendations_by_priority": rec_by_priority,
            "recommendations_by_action": rec_by_action,
        }

    def analyze_query(self, query: str) -> dict[str, Any]:
        """
        Analyze a SQL query for index usage.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary with query analysis results

        """
        result = {
            "query": query,
            "indexes_used": [],
            "tables_scanned": [],
            "execution_plan": [],
            "recommendation": None,
        }

        with self.session_factory() as session:
            try:
                # Get execution plan
                if self.dialect == "postgresql":
                    plan_query = text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
                    plan_result = session.execute(plan_query).scalar()

                    # Extract data from the JSON plan
                    plan_data = json.loads(plan_result) if isinstance(plan_result, str) else plan_result

                    # Extract the plan nodes
                    plan_tree = plan_data[0]["Plan"]
                    result["execution_plan"] = plan_data

                    # Extract indexes used
                    self._extract_indexes_from_plan(plan_tree, result["indexes_used"], result["tables_scanned"])

                elif self.dialect == "sqlite":
                    plan_query = text(f"EXPLAIN QUERY PLAN {query}")
                    plan_rows = session.execute(plan_query).fetchall()

                    # Process the plan rows
                    for row in plan_rows:
                        plan_text = str(row)
                        result["execution_plan"].append(plan_text)

                        # Extract table scans
                        if "SCAN TABLE" in plan_text:
                            table_name = plan_text.split("SCAN TABLE")[1].split()[0]
                            result["tables_scanned"].append(table_name)

                        # Extract index usage
                        if "USING INDEX" in plan_text:
                            parts = plan_text.split("USING INDEX")[1].split()
                            if parts:
                                result["indexes_used"].append(parts[0])

                # Generate recommendation if no indexes were used
                if not result["indexes_used"] and result["tables_scanned"]:
                    result["recommendation"] = self._recommend_index_for_query(query, result["tables_scanned"])

            except Exception as e:
                logger.error(f"Error analyzing query: {e!s}")
                result["error"] = str(e)

        return result

    def _extract_indexes_from_plan(self, plan_node: dict[str, Any],
                                  indexes_used: list[str],
                                  tables_scanned: list[str]) -> None:
        """
        Extract indexes used from a PostgreSQL execution plan.
        
        Args:
            plan_node: Execution plan node
            indexes_used: List to append indexes to
            tables_scanned: List to append scanned tables to

        """
        # Check if this node uses an index
        if "Index Name" in plan_node:
            indexes_used.append(plan_node["Index Name"])

        # Check if this node scans a table
        if "Relation Name" in plan_node:
            tables_scanned.append(plan_node["Relation Name"])

        # Check node type for full table scans
        if plan_node.get("Node Type") == "Seq Scan" and "Relation Name" in plan_node:
            tables_scanned.append(plan_node["Relation Name"])

        # Recursively process child nodes
        for child_key in ["Plans", "Subplans"]:
            if child_key in plan_node and isinstance(plan_node[child_key], list):
                for child_node in plan_node[child_key]:
                    self._extract_indexes_from_plan(child_node, indexes_used, tables_scanned)

    def _recommend_index_for_query(self, query: str, tables: list[str]) -> dict[str, Any]:
        """
        Generate index recommendation for a query.
        
        Args:
            query: SQL query
            tables: Tables accessed in the query
            
        Returns:
            Recommendation dictionary

        """
        # Simple recommendation based on WHERE clauses
        recommendation = {
            "suggested_indexes": [],
        }

        # Extract WHERE conditions
        # This is a simplified approach and might not work for complex queries
        if "WHERE" in query:
            where_clause = query.split("WHERE")[1].split("ORDER BY")[0].split("GROUP BY")[0].split("LIMIT")[0].strip()
            conditions = [cond.strip() for cond in where_clause.split("AND")]

            for condition in conditions:
                # Look for column equality or range conditions
                if "=" in condition:
                    column = condition.split("=")[0].strip()
                    table = self._find_table_for_column(column, tables)
                    if table:
                        recommendation["suggested_indexes"].append({
                            "table": table,
                            "columns": [column.split(".")[-1]],
                            "reason": f"Equality filter on {column}",
                        })
                elif ">" in condition or "<" in condition:
                    column = condition.split(">")[0].split("<")[0].strip()
                    table = self._find_table_for_column(column, tables)
                    if table:
                        recommendation["suggested_indexes"].append({
                            "table": table,
                            "columns": [column.split(".")[-1]],
                            "reason": f"Range filter on {column}",
                        })

        return recommendation

    def _find_table_for_column(self, column: str, tables: list[str]) -> str | None:
        """
        Find the table that a column belongs to.
        
        Args:
            column: Column name or table.column
            tables: List of table names
            
        Returns:
            Table name or None if not found

        """
        # If column already includes table name (e.g., "users.id")
        if "." in column:
            table_name = column.split(".")[0]
            if table_name in tables:
                return table_name

        # Otherwise, search in all tables
        inspector = inspect(self.engine)
        for table in tables:
            columns = [col["name"] for col in inspector.get_columns(table)]
            pure_column = column.split(".")[-1]
            if pure_column in columns:
                return table

        return None

    def recommend_indexes(self) -> list[IndexRecommendation]:
        """
        Generate index recommendations based on database analysis.
        
        Returns:
            List of index recommendations

        """
        recommendations = []

        # 1. Get current index usage
        index_stats = self.analyze_index_usage()

        # 2. Identify ineffective indexes for potential removal
        for stat in index_stats:
            if stat.is_effective is False:
                recommendations.append(IndexRecommendation(
                    action="remove",
                    existing_index_name=stat.index_name,
                    rationale="Index is not effectively used in queries",
                    priority="medium",
                ))

        # 3. Look for missing indexes by analyzing slow queries
        slow_queries = self._get_slow_queries()

        for query_info in slow_queries:
            # Analyze the query plan
            analysis = self.analyze_query(query_info["query"])

            # If recommendations were generated, add them
            if analysis.get("recommendation"):
                for idx_suggestion in analysis["recommendation"].get("suggested_indexes", []):
                    # Create an index definition
                    idx_def = IndexDefinition(
                        table_name=idx_suggestion["table"],
                        column_names=idx_suggestion["columns"],
                    )

                    # Check if this index already exists
                    if not self.check_index_exists(idx_def.index_name, idx_def.table_name):
                        recommendations.append(IndexRecommendation(
                            action="create",
                            index_definition=idx_def,
                            rationale=idx_suggestion.get("reason", "Improve query performance"),
                            estimated_impact=f"May improve slow query executed {query_info.get('count', 1)} times",
                            priority="high" if query_info.get("count", 1) > 100 else "medium",
                        ))

        # 4. Recommend indexes for foreign keys if they don't exist
        fk_recommendations = self._recommend_indexes_for_foreign_keys()
        recommendations.extend(fk_recommendations)

        # 5. Deduplicate recommendations
        deduplicated = []
        seen_names = set()

        for rec in recommendations:
            if rec.action == "create" and rec.index_definition:
                if rec.index_definition.index_name not in seen_names:
                    seen_names.add(rec.index_definition.index_name)
                    deduplicated.append(rec)
            elif rec.action in ["remove", "modify"] and rec.existing_index_name:
                if rec.existing_index_name not in seen_names:
                    seen_names.add(rec.existing_index_name)
                    deduplicated.append(rec)

        return deduplicated

    def _get_slow_queries(self) -> list[dict[str, Any]]:
        """
        Get slow queries from the database, if supported.
        
        Returns:
            List of slow query information

        """
        slow_queries = []

        with self.session_factory() as session:
            try:
                if self.dialect == "postgresql":
                    # PostgreSQL provides query statistics through pg_stat_statements
                    # This extension must be enabled for this to work
                    try:
                        query = text("""
                            SELECT query, calls, total_time / calls as avg_time
                            FROM pg_stat_statements
                            WHERE total_time / calls > 100  -- queries taking > 100ms on average
                            ORDER BY total_time / calls DESC
                            LIMIT 20;
                        """)

                        for row in session.execute(query):
                            slow_queries.append({
                                "query": row.query,
                                "count": row.calls,
                                "avg_time_ms": row.avg_time,
                            })
                    except Exception as e:
                        logger.warning(f"Could not access pg_stat_statements: {e!s}")

                elif self.dialect == "sqlite":
                    # SQLite doesn't track query statistics internally
                    # We would need to implement our own tracking mechanism
                    pass

            except Exception as e:
                logger.error(f"Error getting slow queries: {e!s}")

        return slow_queries

    def _recommend_indexes_for_foreign_keys(self) -> list[IndexRecommendation]:
        """
        Recommend indexes for foreign keys that don't have them.
        
        Returns:
            List of index recommendations for foreign keys

        """
        recommendations = []
        inspector = inspect(self.engine)

        # Get all existing indexes to check against
        existing_indexes = self.get_all_indexes()

        for table_name in inspector.get_table_names():
            # Get foreign keys
            fks = inspector.get_foreign_keys(table_name)

            for fk in fks:
                # Get the local columns that form the foreign key
                local_columns = fk["constrained_columns"]

                # Skip if no columns
                if not local_columns:
                    continue

                # Check if these columns are already indexed
                has_index = False

                # Get the table's indexes
                table_indexes = existing_indexes.get(table_name, [])

                for idx in table_indexes:
                    idx_columns = idx["column_names"]

                    # Check if the first columns of the index match the foreign key columns
                    # This is a simplified check - in reality, we need to consider
                    # the order of columns and whether the FK columns come first
                    if idx_columns and all(col in idx_columns for col in local_columns):
                        has_index = True
                        break

                # If no index exists for this foreign key, recommend one
                if not has_index:
                    idx_def = IndexDefinition(
                        table_name=table_name,
                        column_names=local_columns,
                    )

                    recommendations.append(IndexRecommendation(
                        action="create",
                        index_definition=idx_def,
                        rationale=f"Foreign key to {fk['referred_table']} ({','.join(fk['referred_columns'])}) is not indexed",
                        priority="high",
                    ))

        return recommendations

    def verify_index_usage(self, index_name: str, query: str) -> dict[str, Any]:
        """
        Verify if a specific index is used for a query.
        
        Args:
            index_name: Name of the index to check
            query: SQL query to analyze
            
        Returns:
            Dictionary with verification results

        """
        result = {
            "index_name": index_name,
            "query": query,
            "is_used": False,
            "execution_plan": None,
            "explanation": None,
        }

        with self.session_factory() as session:
            try:
                # Get execution plan
                if self.dialect == "postgresql":
                    plan_query = text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
                    plan_result = session.execute(plan_query).scalar()

                    # Extract data from the JSON plan
                    plan_data = json.loads(plan_result) if isinstance(plan_result, str) else plan_result
                    result["execution_plan"] = plan_data

                    # Check if the index is used
                    def check_node_for_index(node):
                        if node.get("Index Name") == index_name:
                            return True

                        # Check child nodes
                        for child_key in ["Plans", "Subplans"]:
                            if child_key in node and isinstance(node[child_key], list):
                                for child in node[child_key]:
                                    if check_node_for_index(child):
                                        return True
                        return False

                    result["is_used"] = check_node_for_index(plan_data[0]["Plan"])

                elif self.dialect == "sqlite":
                    plan_query = text(f"EXPLAIN QUERY PLAN {query}")
                    plan_rows = session.execute(plan_query).fetchall()

                    plan_text = "\n".join(str(row) for row in plan_rows)
                    result["execution_plan"] = plan_text

                    # Check if the index is mentioned in the plan
                    result["is_used"] = index_name in plan_text or "USING INDEX" in plan_text

                # Provide explanation
                if result["is_used"]:
                    result["explanation"] = f"Index {index_name} is used in the query execution plan"
                else:
                    result["explanation"] = f"Index {index_name} is NOT used in the query execution plan"

            except Exception as e:
                logger.error(f"Error verifying index usage: {e!s}")
                result["error"] = str(e)

        return result

    def get_recommended_indexes(self) -> list[IndexDefinition]:
        """
        Get a list of recommended indexes identified from previous analysis.
        
        Returns:
            List of recommended index definitions

        """
        # These are the recommended indexes based on prior analysis in PERF-6
        indexes = [
            # RecommendationHistory Table
            IndexDefinition(
                table_name="recommendation_history",
                column_names=["status"],
                index_name="idx_recommendation_status",
            ),

            # MigrationState Table
            IndexDefinition(
                table_name="migration_state",
                column_names=["extraction_status", "transformation_status", "loading_status"],
                index_name="idx_migration_state_status",
            ),

            # CustomFieldDefinition Table
            IndexDefinition(
                table_name="custom_field_definitions",
                column_names=["name", "type"],
                index_name="idx_custom_field_name_type",
            ),

            # CustomFieldValue Table
            IndexDefinition(
                table_name="custom_field_values",
                column_names=["field_id", "value_text"],
                index_name="idx_custom_field_value_text",
            ),

            # TestCase Table
            IndexDefinition(
                table_name="test_cases",
                column_names=["created_on", "updated_on"],
                index_name="idx_test_case_dates",
            ),
            IndexDefinition(
                table_name="test_cases",
                column_names=["owner"],
                index_name="idx_test_case_owner",
            ),

            # TestExecution Table
            IndexDefinition(
                table_name="test_executions",
                column_names=["executed_on", "status"],
                index_name="idx_test_execution_date_status",
            ),
            IndexDefinition(
                table_name="test_executions",
                column_names=["executed_by"],
                index_name="idx_test_execution_executed_by",
            ),

            # TestCycle Table
            IndexDefinition(
                table_name="test_cycles",
                column_names=["planned_start_date", "planned_end_date"],
                index_name="idx_test_cycle_dates",
            ),

            # EntityBatchState Table
            IndexDefinition(
                table_name="entity_batch_state",
                column_names=["entity_type", "status"],
                index_name="idx_entity_batch_type_status",
            ),

            # Folder Table
            IndexDefinition(
                table_name="folders",
                column_names=["folder_type", "name"],
                index_name="idx_folder_type_name",
            ),

            # Attachment Table
            IndexDefinition(
                table_name="attachments",
                column_names=["filename", "content_type"],
                index_name="idx_attachment_filename_type",
            ),
        ]

        return indexes

    def create_recommended_indexes(self) -> dict[str, Any]:
        """
        Create all recommended indexes from prior analysis.
        
        Returns:
            Dictionary with results of index creation

        """
        result = {
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "details": [],
        }

        recommended_indexes = self.get_recommended_indexes()

        for idx_def in recommended_indexes:
            # Check if index already exists
            if self.check_index_exists(idx_def.index_name, idx_def.table_name):
                result["skipped_count"] += 1
                result["details"].append({
                    "index_name": idx_def.index_name,
                    "status": "skipped",
                    "reason": "Index already exists",
                })
                continue

            # Create the index
            success = self.create_index(idx_def)

            if success:
                result["success_count"] += 1
                result["details"].append({
                    "index_name": idx_def.index_name,
                    "status": "created",
                    "table_name": idx_def.table_name,
                    "columns": idx_def.column_names,
                })
            else:
                result["failed_count"] += 1
                result["details"].append({
                    "index_name": idx_def.index_name,
                    "status": "failed",
                    "table_name": idx_def.table_name,
                    "columns": idx_def.column_names,
                })

        return result

    def generate_validation_report(self) -> dict[str, Any]:
        """
        Generate a report validating if indexes are being used effectively.
        
        Returns:
            Dictionary with validation report

        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "database_type": self.dialect,
            "indexes_validated": 0,
            "indexes_used": 0,
            "indexes_unused": 0,
            "details": [],
        }

        # Analyze all indexes
        index_stats = self.analyze_index_usage()

        for stat in index_stats:
            validation = {
                "index_name": stat.index_name,
                "table_name": stat.table_name,
                "columns": stat.column_names,
                "is_used": stat.is_effective,
                "usage_count": stat.usage_count,
                "size_bytes": stat.size_bytes,
                "recommendation": None,
            }

            # Increment counters
            report["indexes_validated"] += 1
            if stat.is_effective:
                report["indexes_used"] += 1
            else:
                report["indexes_unused"] += 1
                validation["recommendation"] = "Consider removing this unused index"

            report["details"].append(validation)

        return report


# Utility Functions

def get_index_manager(engine_or_url: Engine | str) -> IndexManager:
    """
    Get an index manager for a database engine or connection URL.
    
    Args:
        engine_or_url: SQLAlchemy engine or connection URL
        
    Returns:
        IndexManager instance

    """
    if isinstance(engine_or_url, str):
        engine = create_engine(engine_or_url)
    else:
        engine = engine_or_url

    return IndexManager(engine)

def optimize_database_indexes(engine_or_url: Engine | str) -> dict[str, Any]:
    """
    Optimize database indexes by creating recommended indexes.
    
    Args:
        engine_or_url: SQLAlchemy engine or connection URL
        
    Returns:
        Dictionary with optimization results

    """
    index_manager = get_index_manager(engine_or_url)
    return index_manager.create_recommended_indexes()

def analyze_database_indexes(engine_or_url: Engine | str) -> dict[str, Any]:
    """
    Analyze database indexes and generate recommendations.
    
    Args:
        engine_or_url: SQLAlchemy engine or connection URL
        
    Returns:
        Dictionary with analysis results

    """
    index_manager = get_index_manager(engine_or_url)
    return index_manager.generate_index_report()

def validate_database_indexes(engine_or_url: Engine | str) -> dict[str, Any]:
    """
    Validate if database indexes are being used effectively.
    
    Args:
        engine_or_url: SQLAlchemy engine or connection URL
        
    Returns:
        Dictionary with validation results

    """
    index_manager = get_index_manager(engine_or_url)
    return index_manager.generate_validation_report()

def create_specific_index(
    engine_or_url: Engine | str,
    table_name: str,
    column_names: list[str],
    index_name: str | None = None,
    index_type: str = "btree",
    unique: bool = False,
) -> bool:
    """
    Create a specific index on a database table.
    
    Args:
        engine_or_url: SQLAlchemy engine or connection URL
        table_name: Name of the table
        column_names: List of column names to index
        index_name: Optional name for the index
        index_type: Type of index (default: "btree")
        unique: Whether the index should enforce uniqueness
        
    Returns:
        True if index was created successfully, False otherwise

    """
    index_manager = get_index_manager(engine_or_url)

    idx_def = IndexDefinition(
        table_name=table_name,
        column_names=column_names,
        index_name=index_name,
        index_type=IndexType(index_type),
        unique=unique,
    )

    return index_manager.create_index(idx_def)
