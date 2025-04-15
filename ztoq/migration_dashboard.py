#!/usr/bin/env python3
"""
Migration monitoring dashboard.

This module provides a web-based dashboard for monitoring migration progress
in real-time using Flask and Chart.js.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, render_template, request
from rich.console import Console
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ztoq.core.db_models import EntityBatchState, MigrationState

# Configure rich console
console = Console()

# Initialize Flask app
app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching for development

# Global variables for database connection
db_url = None
project_key = None
refresh_interval = 10  # Refresh interval in seconds


class MigrationDashboardData:
    """Class for fetching and processing migration data for the dashboard."""

    def __init__(self, db_url: str, project_key: str):
        """
        Initialize the dashboard data provider.

        Args:
            db_url: SQLAlchemy database URL (e.g., 'sqlite:///migration.db')
            project_key: The Zephyr project key to generate the report for

        """
        self.db_url = db_url
        self.project_key = project_key
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def get_migration_state(self) -> dict[str, Any]:
        """
        Get the current migration state.

        Returns:
            Dictionary containing migration state information

        """
        with self.Session() as session:
            state = session.query(MigrationState).filter_by(project_key=self.project_key).first()

            if state:
                return {
                    "project_key": self.project_key,
                    "extraction_status": state.extraction_status or "not_started",
                    "transformation_status": state.transformation_status or "not_started",
                    "loading_status": state.loading_status or "not_started",
                    "error_message": state.error_message,
                    "created_at": state.created_at.isoformat() if state.created_at else None,
                    "updated_at": state.last_updated.isoformat() if state.last_updated else None,
                    "current_timestamp": datetime.now().isoformat(),
                }

            # Return default state if no record exists
            return {
                "project_key": self.project_key,
                "extraction_status": "not_started",
                "transformation_status": "not_started",
                "loading_status": "not_started",
                "error_message": None,
                "created_at": None,
                "updated_at": None,
                "current_timestamp": datetime.now().isoformat(),
            }

    def get_entity_counts(self) -> dict[str, dict[str, int]]:
        """
        Get counts of migrated entities.

        Returns:
            Dictionary containing entity counts by type and stage

        """
        entity_counts = {"source": {}, "transformed": {}, "loaded": {}, "mappings": {}}

        with self.Session() as session:
            # Get counts of mapped entities
            mapping_types = [
                "folder_to_module",
                "testcase_to_testcase",
                "cycle_to_cycle",
                "execution_to_run",
            ]

            for mapping_type in mapping_types:
                try:
                    count = (
                        session.execute(
                            text(
                                """
                        SELECT COUNT(*)
                        FROM entity_mappings
                        WHERE project_key = :project_key
                        AND mapping_type = :mapping_type
                        """,
                            ),
                            {"project_key": self.project_key, "mapping_type": mapping_type},
                        ).scalar()
                        or 0
                    )

                    entity_counts["mappings"][mapping_type] = count
                except Exception:
                    # Handle case where entity_mappings table might not exist yet
                    entity_counts["mappings"][mapping_type] = 0

            # Get source entity counts from batches
            entity_types = [
                "folders",
                "test_cases",
                "test_cycles",
                "test_executions",
            ]

            for entity_type in entity_types:
                # Get batch info for this entity type
                batches = (
                    session.query(EntityBatchState)
                    .filter_by(project_key=self.project_key, entity_type=entity_type)
                    .all()
                )

                if batches:
                    # Sum up the items_count across all batches
                    total_items = sum(batch.items_count for batch in batches)
                    entity_counts["source"][entity_type] = total_items
                else:
                    entity_counts["source"][entity_type] = 0

            # Get transformed entity counts
            transformed_types = [
                "transformed_test_cases",
                "transformed_test_cycles",
                "transformed_test_executions",
            ]

            for entity_type in transformed_types:
                batches = (
                    session.query(EntityBatchState)
                    .filter_by(project_key=self.project_key, entity_type=entity_type)
                    .all()
                )

                if batches:
                    total_processed = sum(
                        batch.processed_count for batch in batches if batch.status == "completed"
                    )
                    entity_counts["transformed"][entity_type] = total_processed
                else:
                    entity_counts["transformed"][entity_type] = 0

            # Get loaded entity counts
            loaded_types = [
                "loaded_test_cases",
                "loaded_test_cycles",
                "loaded_test_executions",
            ]

            for entity_type in loaded_types:
                batches = (
                    session.query(EntityBatchState)
                    .filter_by(project_key=self.project_key, entity_type=entity_type)
                    .all()
                )

                if batches:
                    total_processed = sum(
                        batch.processed_count for batch in batches if batch.status == "completed"
                    )
                    entity_counts["loaded"][entity_type] = total_processed
                else:
                    entity_counts["loaded"][entity_type] = 0

        return entity_counts

    def get_batch_statistics(self) -> dict[str, dict[str, int | float]]:
        """
        Get statistics about batch processing.

        Returns:
            Dictionary containing batch processing statistics by entity type

        """
        batch_stats = {}

        with self.Session() as session:
            # Get all entity types that have batches
            entity_types = []
            result = session.execute(
                text(
                    """
                SELECT DISTINCT entity_type
                FROM entity_batch_state
                WHERE project_key = :project_key
                """,
                ),
                {"project_key": self.project_key},
            )

            for row in result:
                entity_types.append(row[0])

            # Get stats for each entity type
            for entity_type in entity_types:
                batches = (
                    session.query(EntityBatchState)
                    .filter_by(project_key=self.project_key, entity_type=entity_type)
                    .all()
                )

                if batches:
                    # Calculate statistics
                    total_batches = len(batches)
                    completed_batches = sum(1 for batch in batches if batch.status == "completed")
                    failed_batches = sum(1 for batch in batches if batch.status == "failed")
                    pending_batches = sum(
                        1 for batch in batches if batch.status in ["not_started", "in_progress"]
                    )

                    total_items = sum(batch.items_count for batch in batches)
                    processed_items = sum(batch.processed_count for batch in batches)

                    if total_items > 0:
                        completion_percentage = (processed_items / total_items) * 100
                    else:
                        completion_percentage = 0

                    # Determine status timestamps for this entity type
                    started_times = [b.started_at for b in batches if b.started_at]
                    completed_times = [b.completed_at for b in batches if b.completed_at]

                    start_time = min(started_times).isoformat() if started_times else None
                    latest_time = max(completed_times).isoformat() if completed_times else None
                    if not latest_time and started_times:
                        latest_time = max(started_times).isoformat()

                    batch_stats[entity_type] = {
                        "total_batches": total_batches,
                        "completed_batches": completed_batches,
                        "failed_batches": failed_batches,
                        "pending_batches": pending_batches,
                        "total_items": total_items,
                        "processed_items": processed_items,
                        "completion_percentage": completion_percentage,
                        "start_time": start_time,
                        "latest_time": latest_time,
                    }

        return batch_stats

    def get_recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent migration activity from the database.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of dictionaries containing recent activity data

        """
        activity = []

        with self.Session() as session:
            # Get recently updated batches
            recent_batches = (
                session.query(EntityBatchState)
                .filter_by(project_key=self.project_key)
                .order_by(EntityBatchState.last_updated.desc())
                .limit(limit)
                .all()
            )

            for batch in recent_batches:
                activity.append(
                    {
                        "type": "batch",
                        "timestamp": batch.last_updated.isoformat() if batch.last_updated else None,
                        "entity_type": batch.entity_type,
                        "batch_number": batch.batch_number,
                        "status": batch.status,
                        "processed_count": batch.processed_count,
                        "total_count": batch.items_count,
                        "error_message": batch.error_message,
                    },
                )

            # Get recent validation issues
            try:
                # Check if validation_issues table exists
                table_exists = False
                result = session.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='validation_issues'
                    UNION
                    SELECT tablename FROM pg_catalog.pg_tables
                    WHERE schemaname='public' AND tablename='validation_issues'
                    """,
                    ),
                )

                for row in result:
                    table_exists = True
                    break

                if table_exists:
                    recent_issues = session.execute(
                        text(
                            """
                        SELECT id, rule_id, level, message, entity_id, scope, phase,
                                   created_on, resolved, context
                        FROM validation_issues
                        WHERE project_key = :project_key AND resolved = 0
                        ORDER BY created_on DESC
                        LIMIT :limit
                        """,
                        ),
                        {"project_key": self.project_key, "limit": limit},
                    ).fetchall()

                    for issue in recent_issues:
                        context = {}
                        if issue.context:
                            try:
                                context = json.loads(issue.context)
                            except:
                                pass

                        activity.append(
                            {
                                "type": "validation",
                                "timestamp": issue.created_on
                                if isinstance(issue.created_on, str)
                                else issue.created_on.isoformat(),
                                "level": issue.level,
                                "scope": issue.scope,
                                "phase": issue.phase,
                                "message": issue.message,
                                "entity_id": issue.entity_id,
                                "rule_id": issue.rule_id,
                                "context": context,
                            },
                        )
            except Exception as e:
                logger.error(f"Error retrieving validation issues: {e!s}")

        # Sort combined activity by timestamp (most recent first)
        activity.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "", reverse=True)

        # Limit to requested number of items
        return activity[:limit]

    def get_validation_statistics(self) -> dict[str, Any]:
        """
        Get statistics about validation issues.

        Returns:
            Dictionary containing validation issue statistics

        """
        validation_stats = {
            "issues_by_level": {},
            "issues_by_scope": {},
            "issues_by_phase": {},
            "critical_issues": 0,
            "error_issues": 0,
            "warning_issues": 0,
            "info_issues": 0,
            "total_issues": 0,
            "has_critical_issues": False,
            "recent_issues": [],
        }

        with self.Session() as session:
            try:
                # Check if validation_issues table exists
                table_exists = False
                result = session.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='validation_issues'
                    UNION
                    SELECT tablename FROM pg_catalog.pg_tables
                    WHERE schemaname='public' AND tablename='validation_issues'
                    """,
                    ),
                )

                for row in result:
                    table_exists = True
                    break

                if not table_exists:
                    return validation_stats

                # Get total count of issues
                total_count = (
                    session.execute(
                        text(
                            """
                    SELECT COUNT(*)
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    """,
                        ),
                        {"project_key": self.project_key},
                    ).scalar()
                    or 0
                )

                validation_stats["total_issues"] = total_count

                # Get counts by level
                level_counts = session.execute(
                    text(
                        """
                    SELECT level, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY level
                    """,
                    ),
                    {"project_key": self.project_key},
                ).fetchall()

                for level_count in level_counts:
                    level = level_count.level
                    count = level_count.count

                    validation_stats["issues_by_level"][level] = count

                    if level == "critical":
                        validation_stats["critical_issues"] = count
                        validation_stats["has_critical_issues"] = count > 0
                    elif level == "error":
                        validation_stats["error_issues"] = count
                    elif level == "warning":
                        validation_stats["warning_issues"] = count
                    elif level == "info":
                        validation_stats["info_issues"] = count

                # Get counts by scope
                scope_counts = session.execute(
                    text(
                        """
                    SELECT scope, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY scope
                    """,
                    ),
                    {"project_key": self.project_key},
                ).fetchall()

                for scope_count in scope_counts:
                    validation_stats["issues_by_scope"][scope_count.scope] = scope_count.count

                # Get counts by phase
                phase_counts = session.execute(
                    text(
                        """
                    SELECT phase, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY phase
                    """,
                    ),
                    {"project_key": self.project_key},
                ).fetchall()

                for phase_count in phase_counts:
                    validation_stats["issues_by_phase"][phase_count.phase] = phase_count.count

                # Get most recent critical and error issues
                recent_issues = session.execute(
                    text(
                        """
                    SELECT id, rule_id, level, message, entity_id, scope, phase, created_on
                    FROM validation_issues
                    WHERE project_key = :project_key
                    AND resolved = 0
                    AND level IN ('critical', 'error')
                    ORDER BY created_on DESC
                    LIMIT 5
                    """,
                    ),
                    {"project_key": self.project_key},
                ).fetchall()

                for issue in recent_issues:
                    validation_stats["recent_issues"].append(
                        {
                            "id": issue.id,
                            "rule_id": issue.rule_id,
                            "level": issue.level,
                            "message": issue.message,
                            "entity_id": issue.entity_id,
                            "scope": issue.scope,
                            "phase": issue.phase,
                            "created_on": issue.created_on
                            if isinstance(issue.created_on, str)
                            else issue.created_on.isoformat(),
                        },
                    )

            except Exception as e:
                logger.error(f"Error retrieving validation statistics: {e!s}")

        return validation_stats

    def get_status_summary(self) -> dict[str, Any]:
        """
        Get a summary of the migration status.

        Returns:
            Dictionary containing migration status summary

        """
        # Get data from other methods
        state = self.get_migration_state()
        entity_counts = self.get_entity_counts()
        batch_stats = self.get_batch_statistics()
        validation_stats = self.get_validation_statistics()

        # Calculate overall progress percentages
        total_source = sum(entity_counts["source"].values())
        total_transformed = sum(entity_counts["transformed"].values())
        total_loaded = sum(entity_counts["loaded"].values())

        extraction_percentage = 0
        transformation_percentage = 0
        loading_percentage = 0
        overall_percentage = 0

        if total_source > 0:
            extraction_percentage = 100  # If we have source counts, extraction is complete

            if total_transformed > 0:
                transformation_percentage = (total_transformed / total_source) * 100

            if total_loaded > 0:
                loading_percentage = (total_loaded / total_source) * 100

        # Calculate overall percentage as weighted average
        if total_source > 0:
            # Weight: extraction 20%, transformation 30%, loading 50%
            overall_percentage = (
                0.2 * extraction_percentage
                + 0.3 * transformation_percentage
                + 0.5 * loading_percentage
            )

        # Count active and failed batches
        active_batches = 0
        failed_batches = 0

        for entity_type, stats in batch_stats.items():
            active_batches += stats.get("pending_batches", 0)
            failed_batches += stats.get("failed_batches", 0)

        # Build summary
        return {
            "project_key": self.project_key,
            "state": state,
            "progress": {
                "extraction": extraction_percentage,
                "transformation": transformation_percentage,
                "loading": loading_percentage,
                "overall": overall_percentage,
            },
            "entities": {
                "total_source": total_source,
                "total_transformed": total_transformed,
                "total_loaded": total_loaded,
            },
            "batches": {"active_batches": active_batches, "failed_batches": failed_batches},
            "validation": {
                "total_issues": validation_stats["total_issues"],
                "critical_issues": validation_stats["critical_issues"],
                "error_issues": validation_stats["error_issues"],
                "warning_issues": validation_stats["warning_issues"],
                "info_issues": validation_stats["info_issues"],
                "has_critical_issues": validation_stats["has_critical_issues"],
                "recent_issues": validation_stats["recent_issues"],
            },
        }


# Flask routes
@app.route("/")
def index():
    """Render the dashboard page."""
    return render_template(
        "dashboard.html", project_key=project_key, refresh_interval=refresh_interval,
    )


@app.route("/api/status")
def get_status():
    """API endpoint to get migration status data."""
    data_provider = MigrationDashboardData(db_url, project_key)
    summary = data_provider.get_status_summary()
    return jsonify(summary)


@app.route("/api/entities")
def get_entities():
    """API endpoint to get entity count data."""
    data_provider = MigrationDashboardData(db_url, project_key)
    entity_counts = data_provider.get_entity_counts()
    return jsonify(entity_counts)


@app.route("/api/batches")
def get_batches():
    """API endpoint to get batch statistics data."""
    data_provider = MigrationDashboardData(db_url, project_key)
    batch_stats = data_provider.get_batch_statistics()
    return jsonify(batch_stats)


@app.route("/api/activity")
def get_activity():
    """API endpoint to get recent activity data."""
    limit = request.args.get("limit", default=10, type=int)
    data_provider = MigrationDashboardData(db_url, project_key)
    activity = data_provider.get_recent_activity(limit)
    return jsonify(activity)


@app.route("/api/validation")
def get_validation():
    """API endpoint to get validation statistics."""
    data_provider = MigrationDashboardData(db_url, project_key)
    validation_stats = data_provider.get_validation_statistics()
    return jsonify(validation_stats)


@app.route("/api/validation/issues")
def get_validation_issues():
    """API endpoint to get validation issues with filtering."""
    level = request.args.get("level")
    scope = request.args.get("scope")
    phase = request.args.get("phase")
    limit = request.args.get("limit", default=50, type=int)

    with MigrationDashboardData(db_url, project_key).Session() as session:
        try:
            # Build query
            query = """
            SELECT id, rule_id, level, message, entity_id, scope, phase,
                       created_on, resolved, context
            FROM validation_issues
            WHERE project_key = :project_key AND resolved = 0
            """
            params = {"project_key": project_key}

            if level:
                query += " AND level = :level"
                params["level"] = level

            if scope:
                query += " AND scope = :scope"
                params["scope"] = scope

            if phase:
                query += " AND phase = :phase"
                params["phase"] = phase

            query += " ORDER BY created_on DESC LIMIT :limit"
            params["limit"] = limit

            result = session.execute(text(query), params).fetchall()

            issues = []
            for issue in result:
                context = {}
                if issue.context:
                    try:
                        context = json.loads(issue.context)
                    except:
                        pass

                issues.append(
                    {
                        "id": issue.id,
                        "rule_id": issue.rule_id,
                        "level": issue.level,
                        "message": issue.message,
                        "entity_id": issue.entity_id,
                        "scope": issue.scope,
                        "phase": issue.phase,
                        "created_on": issue.created_on
                        if isinstance(issue.created_on, str)
                        else issue.created_on.isoformat(),
                        "context": context,
                    },
                )

            return jsonify(issues)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/all")
def get_all_data():
    """API endpoint to get all dashboard data in a single request."""
    data_provider = MigrationDashboardData(db_url, project_key)

    return jsonify(
        {
            "status": data_provider.get_status_summary(),
            "entities": data_provider.get_entity_counts(),
            "batches": data_provider.get_batch_statistics(),
            "activity": data_provider.get_recent_activity(),
            "validation": data_provider.get_validation_statistics(),
        },
    )


def create_dashboard_templates():
    """Create HTML templates for the dashboard."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    # Create directories if they don't exist
    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)

    # Create dashboard.html template
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZTOQ Migration Dashboard - {{ project_key }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.min.js"></script>
    <style>
        body {
            padding-top: 20px;
            padding-bottom: 40px;
            background-color: #f5f5f5;
        }
        .progress-card {
            height: 100%;
        }
        .progress-card .card-body {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .progress {
            height: 25px;
            margin-bottom: 10px;
        }
        .progress-bar {
            font-size: 14px;
            line-height: 25px;
        }
        .status-badge {
            font-size: 0.9rem;
            padding: 8px;
            margin: 5px 0;
            width: 100%;
            text-align: center;
        }
        .entity-count {
            font-size: 2rem;
            margin-bottom: 0;
        }
        .refresh-time {
            font-size: 0.8rem;
            color: #6c757d;
            text-align: right;
            margin-top: 10px;
        }
        .chart-container {
            position: relative;
            height: 250px;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">ZTOQ Migration Dashboard - Project: {{ project_key }}</h4>
                        <button id="refresh-btn" class="btn btn-sm btn-light">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-clockwise" viewBox="0 0 16 16">
                                <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
                                <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
                            </svg>
                            Refresh
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <!-- Overall Progress -->
                            <div class="col-md-6">
                                <h5>Overall Migration Progress</h5>
                                <div class="progress mb-3">
                                    <div id="overall-progress" class="progress-bar progress-bar-striped progress-bar-animated"
                                         role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                        0%
                                    </div>
                                </div>

                                <div class="row">
                                    <div class="col-md-4">
                                        <h6>Extraction</h6>
                                        <div class="progress">
                                            <div id="extraction-progress" class="progress-bar bg-info"
                                                 role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                                0%
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <h6>Transformation</h6>
                                        <div class="progress">
                                            <div id="transformation-progress" class="progress-bar bg-warning"
                                                 role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                                0%
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <h6>Loading</h6>
                                        <div class="progress">
                                            <div id="loading-progress" class="progress-bar bg-success"
                                                 role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                                0%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Migration Status -->
                            <div class="col-md-6">
                                <h5>Migration Status</h5>
                                <div class="row">
                                    <div class="col-md-4">
                                        <div id="extraction-status" class="status-badge badge bg-secondary">
                                            Extraction: Not Started
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div id="transformation-status" class="status-badge badge bg-secondary">
                                            Transformation: Not Started
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div id="loading-status" class="status-badge badge bg-secondary">
                                            Loading: Not Started
                                        </div>
                                    </div>
                                </div>

                                <div class="alert alert-info mt-3">
                                    <div class="row">
                                        <div class="col-6">
                                            <div>Active Batches: <span id="active-batches" class="fw-bold">0</span></div>
                                            <div>Failed Batches: <span id="failed-batches" class="fw-bold">0</span></div>
                                        </div>
                                        <div class="col-6">
                                            <div id="last-update-time" class="refresh-time text-end">
                                                Last updated: Never
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <!-- Entity Counts -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Entity Counts</h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-md-4">
                                <h6>Source</h6>
                                <p id="source-count" class="entity-count">0</p>
                                <small>Total Entities</small>
                            </div>
                            <div class="col-md-4">
                                <h6>Transformed</h6>
                                <p id="transformed-count" class="entity-count">0</p>
                                <small>Processed</small>
                            </div>
                            <div class="col-md-4">
                                <h6>Loaded</h6>
                                <p id="loaded-count" class="entity-count">0</p>
                                <small>Completed</small>
                            </div>
                        </div>

                        <div class="chart-container mt-3">
                            <canvas id="entity-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Batch Status -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-warning text-dark">
                        <h5 class="mb-0">Batch Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="batch-chart"></canvas>
                        </div>

                        <div class="table-responsive mt-3">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Type</th>
                                        <th>Total</th>
                                        <th>Completed</th>
                                        <th>Failed</th>
                                    </tr>
                                </thead>
                                <tbody id="batch-table-body">
                                    <!-- Batch data will be inserted here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Recent Activity -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Recent Activity</h5>
                    </div>
                    <div class="card-body">
                        <div class="list-group" id="activity-list">
                            <!-- Activity items will be inserted here -->
                            <div class="list-group-item">
                                <p class="mb-0">No activity yet</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <!-- Entity Progress Details -->
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Entity Progress Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="chart-container">
                                    <canvas id="progress-chart"></canvas>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="chart-container">
                                    <canvas id="entity-type-chart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Validation Section -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header bg-danger text-white">
                        <h5 class="mb-0">Validation Issues</h5>
                    </div>
                    <div class="card-body">
                        <div id="validation-alert" class="alert alert-warning d-none">
                            <strong>Critical Issues Detected!</strong> There are validation issues that require attention.
                        </div>
                        <div class="row text-center mb-3">
                            <div class="col-md-3">
                                <h6>Critical</h6>
                                <p id="critical-issues-count" class="entity-count text-danger">0</p>
                            </div>
                            <div class="col-md-3">
                                <h6>Error</h6>
                                <p id="error-issues-count" class="entity-count text-warning">0</p>
                            </div>
                            <div class="col-md-3">
                                <h6>Warning</h6>
                                <p id="warning-issues-count" class="entity-count text-primary">0</p>
                            </div>
                            <div class="col-md-3">
                                <h6>Info</h6>
                                <p id="info-issues-count" class="entity-count text-info">0</p>
                            </div>
                        </div>
                        <div class="chart-container mt-3">
                            <canvas id="validation-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header bg-danger text-white">
                        <h5 class="mb-0">Recent Critical/Error Issues</h5>
                    </div>
                    <div class="card-body">
                        <div class="list-group" id="validation-issues-list">
                            <!-- Validation issues will be inserted here -->
                            <div class="list-group-item">
                                <p class="mb-0">No validation issues</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Error Alert (hidden by default) -->
        <div id="error-alert" class="alert alert-danger mt-4 d-none">
            <h5>Error</h5>
            <p id="error-message"></p>
        </div>
    </div>

    <script>
        // Charts
        let entityChart = null;
        let batchChart = null;
        let progressChart = null;
        let entityTypeChart = null;
        let validationChart = null;

        // Configuration
        const refreshInterval = {{ refresh_interval }} * 1000; // Convert to milliseconds
        let autoRefreshTimer;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            fetchDashboardData();

            // Set up auto-refresh
            autoRefreshTimer = setInterval(fetchDashboardData, refreshInterval);

            // Manual refresh button
            document.getElementById('refresh-btn').addEventListener('click', function() {
                fetchDashboardData();

                // Reset the auto-refresh timer
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = setInterval(fetchDashboardData, refreshInterval);
            });
        });

        // Fetch dashboard data
        function fetchDashboardData() {
            fetch('/api/all')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    updateDashboard(data);
                    hideError();
                })
                .catch(error => {
                    showError('Failed to fetch dashboard data: ' + error.message);
                    console.error('Error fetching dashboard data:', error);
                });
        }

        // Update dashboard with new data
        function updateDashboard(data) {
            updateStatusSection(data.status);
            updateEntityCounts(data.entities);
            updateBatchStatus(data.batches);
            updateRecentActivity(data.activity);
            updateValidationSection(data.status.validation);
            updateCharts(data);

            // Update last refresh time
            const now = new Date();
            document.getElementById('last-update-time').textContent =
                'Last updated: ' + now.toLocaleTimeString();
        }

        // Update validation section with validation issues
        function updateValidationSection(validation) {
            // Update issue counts
            document.getElementById('critical-issues-count').textContent = validation.critical_issues;
            document.getElementById('error-issues-count').textContent = validation.error_issues;
            document.getElementById('warning-issues-count').textContent = validation.warning_issues;
            document.getElementById('info-issues-count').textContent = validation.info_issues;

            // Show/hide validation alert
            const validationAlert = document.getElementById('validation-alert');
            if (validation.has_critical_issues) {
                validationAlert.classList.remove('d-none');
            } else {
                validationAlert.classList.add('d-none');
            }

            // Update recent issues list
            updateValidationIssuesList(validation.recent_issues);
        }

        // Update the validation issues list
        function updateValidationIssuesList(issues) {
            const issuesList = document.getElementById('validation-issues-list');
            issuesList.innerHTML = '';

            if (issues.length === 0) {
                issuesList.innerHTML = `
                    <div class="list-group-item">
                        <p class="mb-0">No validation issues</p>
                    </div>
                `;
                return;
            }

            // Add issue items
            issues.forEach(issue => {
                let badgeClass = 'badge ';
                switch (issue.level) {
                    case 'critical':
                        badgeClass += 'bg-danger';
                        break;
                    case 'error':
                        badgeClass += 'bg-warning text-dark';
                        break;
                    case 'warning':
                        badgeClass += 'bg-primary';
                        break;
                    case 'info':
                        badgeClass += 'bg-info text-dark';
                        break;
                    default:
                        badgeClass += 'bg-secondary';
                }

                const timestamp = new Date(issue.created_on).toLocaleString();
                const displayScope = issue.scope.replace('_', ' ')
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');

                const item = document.createElement('div');
                item.className = 'list-group-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span><span class="${badgeClass}">${issue.level}</span> ${displayScope}</span>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    <div class="small">${issue.message}</div>
                    <div class="small text-muted">Entity ID: ${issue.entity_id}, Rule: ${issue.rule_id}</div>
                `;

                issuesList.appendChild(item);
            });
        }

        // Update migration status section
        function updateStatusSection(status) {
            // Update progress bars
            const overallProgress = document.getElementById('overall-progress');
            const extractionProgress = document.getElementById('extraction-progress');
            const transformationProgress = document.getElementById('transformation-progress');
            const loadingProgress = document.getElementById('loading-progress');

            const overallValue = Math.round(status.progress.overall);
            const extractionValue = Math.round(status.progress.extraction);
            const transformationValue = Math.round(status.progress.transformation);
            const loadingValue = Math.round(status.progress.loading);

            overallProgress.style.width = overallValue + '%';
            overallProgress.textContent = overallValue + '%';
            overallProgress.setAttribute('aria-valuenow', overallValue);

            extractionProgress.style.width = extractionValue + '%';
            extractionProgress.textContent = extractionValue + '%';
            extractionProgress.setAttribute('aria-valuenow', extractionValue);

            transformationProgress.style.width = transformationValue + '%';
            transformationProgress.textContent = transformationValue + '%';
            transformationProgress.setAttribute('aria-valuenow', transformationValue);

            loadingProgress.style.width = loadingValue + '%';
            loadingProgress.textContent = loadingValue + '%';
            loadingProgress.setAttribute('aria-valuenow', loadingValue);

            // Update status badges
            updateStatusBadge('extraction-status', 'Extraction', status.state.extraction_status);
            updateStatusBadge('transformation-status', 'Transformation', status.state.transformation_status);
            updateStatusBadge('loading-status', 'Loading', status.state.loading_status);

            // Update batch counts
            document.getElementById('active-batches').textContent = status.batches.active_batches;
            document.getElementById('failed-batches').textContent = status.batches.failed_batches;
        }

        // Update status badge with appropriate color
        function updateStatusBadge(elementId, label, status) {
            const badge = document.getElementById(elementId);
            let badgeClass = 'badge ';
            let statusText = status.replace('_', ' ');

            // Capitalize first letter of each word
            statusText = statusText.split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');

            switch (status) {
                case 'completed':
                    badgeClass += 'bg-success';
                    break;
                case 'in_progress':
                    badgeClass += 'bg-primary';
                    break;
                case 'failed':
                    badgeClass += 'bg-danger';
                    break;
                default:
                    badgeClass += 'bg-secondary';
            }

            badge.className = 'status-badge ' + badgeClass;
            badge.textContent = label + ': ' + statusText;
        }

        // Update entity counts section
        function updateEntityCounts(entities) {
            const sourceTotal = Object.values(entities.source).reduce((a, b) => a + b, 0);

            const transformedTotal = Object.values(entities.transformed)
                .reduce((a, b) => a + b, 0);

            const loadedTotal = Object.values(entities.loaded)
                .reduce((a, b) => a + b, 0);

            document.getElementById('source-count').textContent = sourceTotal;
            document.getElementById('transformed-count').textContent = transformedTotal;
            document.getElementById('loaded-count').textContent = loadedTotal;
        }

        // Update batch status section
        function updateBatchStatus(batches) {
            const tableBody = document.getElementById('batch-table-body');
            tableBody.innerHTML = '';

            // Add rows for each batch type
            Object.entries(batches).forEach(([entityType, stats]) => {
                const displayType = entityType.replace('_', ' ')
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${displayType}</td>
                    <td>${stats.total_batches}</td>
                    <td>${stats.completed_batches}</td>
                    <td>${stats.failed_batches}</td>
                `;

                tableBody.appendChild(row);
            });
        }

        // Update recent activity section
        function updateRecentActivity(activities) {
            const activityList = document.getElementById('activity-list');
            activityList.innerHTML = '';

            if (activities.length === 0) {
                activityList.innerHTML = `
                    <div class="list-group-item">
                        <p class="mb-0">No activity yet</p>
                    </div>
                `;
                return;
            }

            // Add activity items
            activities.forEach(activity => {
                const displayType = activity.entity_type.replace('_', ' ')
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');

                const timestamp = new Date(activity.timestamp).toLocaleTimeString();

                let badgeClass = 'badge ';
                switch (activity.status) {
                    case 'completed':
                        badgeClass += 'bg-success';
                        break;
                    case 'in_progress':
                        badgeClass += 'bg-primary';
                        break;
                    case 'failed':
                        badgeClass += 'bg-danger';
                        break;
                    default:
                        badgeClass += 'bg-secondary';
                }

                let error = '';
                if (activity.error_message) {
                    error = `<div class="text-danger small mt-1">${activity.error_message}</div>`;
                }

                const item = document.createElement('div');
                item.className = 'list-group-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span><span class="${badgeClass}">${activity.status}</span> ${displayType}</span>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    <div class="small">Batch #${activity.batch_number}: ${activity.processed_count}/${activity.total_count}</div>
                    ${error}
                `;

                activityList.appendChild(item);
            });
        }

        // Update all charts
        function updateCharts(data) {
            updateEntityChart(data.entities);
            updateBatchChart(data.batches);
            updateProgressChart(data.entities);
            updateEntityTypeChart(data.entities);
            updateValidationChart(data.validation);
        }

        // Update validation chart (pie chart showing validation issues by level)
        function updateValidationChart(validation) {
            // Prepare data
            const levels = ['critical', 'error', 'warning', 'info'];
            const labels = ['Critical', 'Error', 'Warning', 'Info'];
            const data = [
                validation.critical_issues || 0,
                    validation.error_issues || 0,
                    validation.warning_issues || 0,
                    validation.info_issues || 0
            ];

            // Don't render empty chart
            if (data.reduce((a, b) => a + b, 0) === 0) {
                return;
            }

            // Create or update chart
            const ctx = document.getElementById('validation-chart').getContext('2d');

            if (validationChart) {
                validationChart.data.datasets[0].data = data;
                validationChart.update();
            } else {
                validationChart = new Chart(ctx, {
                    type: 'pie',
                        data: {
                        labels: labels,
                            datasets: [{
                            data: data,
                                backgroundColor: [
                                'rgba(220, 53, 69, 0.6)',  // Red for critical
                                'rgba(255, 193, 7, 0.6)',  // Yellow for error
                                'rgba(0, 123, 255, 0.6)',  // Blue for warning
                                'rgba(23, 162, 184, 0.6)'  // Cyan for info
                            ],
                                borderColor: [
                                'rgba(220, 53, 69, 1)',
                                    'rgba(255, 193, 7, 1)',
                                    'rgba(0, 123, 255, 1)',
                                    'rgba(23, 162, 184, 1)'
                            ],
                                borderWidth: 1
                        }]
                    },
                        options: {
                        responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            title: {
                                display: true,
                                    text: 'Validation Issues by Level'
                            },
                                legend: {
                                position: 'bottom',
                                }
                        }
                    }
                });
            }
        }

        // Update entity chart (stacked bar chart)
        function updateEntityChart(entities) {
            // Prepare data
            const entityTypes = {
                'folders': 'Folders',
                    'test_cases': 'Test Cases',
                    'test_cycles': 'Test Cycles',
                    'test_executions': 'Test Executions'
            };

            const labels = Object.values(entityTypes);
            const sourceData = Object.keys(entityTypes).map(key => entities.source[key] || 0);
            const transformedData = [];
            const loadedData = [];

            Object.keys(entityTypes).forEach(key => {
                transformedData.push(entities.transformed['transformed_' + key] || 0);
                loadedData.push(entities.loaded['loaded_' + key] || 0);
            });

            // Create or update chart
            const ctx = document.getElementById('entity-chart').getContext('2d');

            if (entityChart) {
                entityChart.data.datasets[0].data = sourceData;
                entityChart.data.datasets[1].data = transformedData;
                entityChart.data.datasets[2].data = loadedData;
                entityChart.update();
            } else {
                entityChart = new Chart(ctx, {
                    type: 'bar',
                        data: {
                        labels: labels,
                            datasets: [
                            {
                                label: 'Source',
                                    data: sourceData,
                                    backgroundColor: 'rgba(0, 123, 255, 0.6)',
                                    borderColor: 'rgba(0, 123, 255, 1)',
                                    borderWidth: 1
                            },
                                {
                                label: 'Transformed',
                                    data: transformedData,
                                    backgroundColor: 'rgba(255, 193, 7, 0.6)',
                                    borderColor: 'rgba(255, 193, 7, 1)',
                                    borderWidth: 1
                            },
                                {
                                label: 'Loaded',
                                    data: loadedData,
                                    backgroundColor: 'rgba(40, 167, 69, 0.6)',
                                    borderColor: 'rgba(40, 167, 69, 1)',
                                    borderWidth: 1
                            }
                        ]
                    },
                        options: {
                        responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            legend: {
                                position: 'top',
                                },
                                tooltip: {
                                mode: 'index',
                                    intersect: false,
                                }
                        },
                            scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
        }

        // Update batch chart (pie chart)
        function updateBatchChart(batches) {
            // Count total batches by status
            let completed = 0;
            let failed = 0;
            let pending = 0;

            Object.values(batches).forEach(stats => {
                completed += stats.completed_batches;
                failed += stats.failed_batches;
                pending += stats.pending_batches;
            });

            // Create or update chart
            const ctx = document.getElementById('batch-chart').getContext('2d');

            if (batchChart) {
                batchChart.data.datasets[0].data = [completed, failed, pending];
                batchChart.update();
            } else {
                batchChart = new Chart(ctx, {
                    type: 'pie',
                        data: {
                        labels: ['Completed', 'Failed', 'Pending'],
                            datasets: [{
                            data: [completed, failed, pending],
                                backgroundColor: [
                                'rgba(40, 167, 69, 0.6)',  // Green for completed
                                'rgba(220, 53, 69, 0.6)',  // Red for failed
                                'rgba(108, 117, 125, 0.6)' // Gray for pending
                            ],
                                borderColor: [
                                'rgba(40, 167, 69, 1)',
                                    'rgba(220, 53, 69, 1)',
                                    'rgba(108, 117, 125, 1)'
                            ],
                                borderWidth: 1
                        }]
                    },
                        options: {
                        responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            legend: {
                                position: 'bottom',
                                }
                        }
                    }
                });
            }
        }

        // Update progress chart (bar chart showing completion percentages)
        function updateProgressChart(entities) {
            // Calculate completion percentages for each entity type
            const entityTypes = {
                'folders': 'Folders',
                    'test_cases': 'Test Cases',
                    'test_cycles': 'Test Cycles',
                    'test_executions': 'Test Executions'
            };

            const labels = Object.values(entityTypes);
            const percentages = [];

            Object.keys(entityTypes).forEach(key => {
                const sourceCount = entities.source[key] || 0;
                const loadedCount = entities.loaded['loaded_' + key] || 0;

                const percentage = sourceCount > 0
                    ? (loadedCount / sourceCount) * 100
                    : 0;

                percentages.push(Math.round(percentage * 10) / 10); // Round to 1 decimal place
            });

            // Create or update chart
            const ctx = document.getElementById('progress-chart').getContext('2d');

            if (progressChart) {
                progressChart.data.datasets[0].data = percentages;
                progressChart.update();
            } else {
                progressChart = new Chart(ctx, {
                    type: 'bar',
                        data: {
                        labels: labels,
                            datasets: [{
                            label: 'Completion %',
                                data: percentages,
                                backgroundColor: [
                                'rgba(23, 162, 184, 0.6)',
                                    'rgba(0, 123, 255, 0.6)',
                                    'rgba(255, 193, 7, 0.6)',
                                    'rgba(40, 167, 69, 0.6)'
                            ],
                                borderColor: [
                                'rgba(23, 162, 184, 1)',
                                    'rgba(0, 123, 255, 1)',
                                    'rgba(255, 193, 7, 1)',
                                    'rgba(40, 167, 69, 1)'
                            ],
                                borderWidth: 1
                        }]
                    },
                        options: {
                        responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            title: {
                                display: true,
                                    text: 'Migration Completion Percentage by Entity Type'
                            },
                                legend: {
                                display: false
                            }
                        },
                            scales: {
                            y: {
                                beginAtZero: true,
                                    max: 100,
                                    title: {
                                    display: true,
                                        text: 'Percentage (%)'
                                }
                            }
                        }
                    }
                });
            }
        }

        // Update entity type chart (doughnut chart)
        function updateEntityTypeChart(entities) {
            // Count each entity type from the source data
            const entityTypes = {
                'folders': 'Folders',
                    'test_cases': 'Test Cases',
                    'test_cycles': 'Test Cycles',
                    'test_executions': 'Test Executions'
            };

            const labels = Object.values(entityTypes);
            const data = Object.keys(entityTypes).map(key => entities.source[key] || 0);

            // Create or update chart
            const ctx = document.getElementById('entity-type-chart').getContext('2d');

            if (entityTypeChart) {
                entityTypeChart.data.datasets[0].data = data;
                entityTypeChart.update();
            } else {
                entityTypeChart = new Chart(ctx, {
                    type: 'doughnut',
                        data: {
                        labels: labels,
                            datasets: [{
                            data: data,
                                backgroundColor: [
                                'rgba(23, 162, 184, 0.6)',
                                    'rgba(0, 123, 255, 0.6)',
                                    'rgba(255, 193, 7, 0.6)',
                                    'rgba(40, 167, 69, 0.6)'
                            ],
                                borderColor: [
                                'rgba(23, 162, 184, 1)',
                                    'rgba(0, 123, 255, 1)',
                                    'rgba(255, 193, 7, 1)',
                                    'rgba(40, 167, 69, 1)'
                            ],
                                borderWidth: 1
                        }]
                    },
                        options: {
                        responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            title: {
                                display: true,
                                    text: 'Entity Type Distribution'
                            },
                                legend: {
                                position: 'bottom',
                                }
                        }
                    }
                });
            }
        }

        // Show error alert
        function showError(message) {
            const errorAlert = document.getElementById('error-alert');
            const errorMessage = document.getElementById('error-message');

            errorMessage.textContent = message;
            errorAlert.classList.remove('d-none');
        }

        // Hide error alert
        function hideError() {
            const errorAlert = document.getElementById('error-alert');
            errorAlert.classList.add('d-none');
        }
    </script>
</body>
</html>
    """

    with open(os.path.join(templates_dir, "dashboard.html"), "w") as f:
        f.write(dashboard_html)

    console.print("Dashboard templates created successfully.")


def parse_db_url(
    db_type: str,
    host: str | None = None,
    port: int | None = None,
    name: str | None = None,
    user: str | None = None,
    password: str | None = None,
    path: str | None = None,
) -> str:
    """
    Parse database connection parameters into a SQLAlchemy URL.

    Args:
        db_type: Database type (sqlite or postgresql)
        host: Database host (for postgresql)
        port: Database port (for postgresql)
        name: Database name (for postgresql)
        user: Database user (for postgresql)
        password: Database password (for postgresql)
        path: Database file path (for sqlite)

    Returns:
        SQLAlchemy database URL

    """
    if db_type == "sqlite":
        if not path:
            path = "ztoq_data.db"
        return f"sqlite:///{path}"
    if db_type == "postgresql":
        if not all([host, name, user, password]):
            raise ValueError("PostgreSQL connection requires host, name, user, and password")
        port_str = f":{port}" if port else ""
        return f"postgresql://{user}:{password}@{host}{port_str}/{name}"
    raise ValueError(f"Unsupported database type: {db_type}")


def main() -> None:
    """Main entry point for the migration dashboard web application."""
    parser = argparse.ArgumentParser(description="Start a migration monitoring dashboard")

    # Database connection parameters
    parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgresql"],
        default="sqlite",
        help="Database type (sqlite or postgresql)",
    )
    parser.add_argument("--db-path", help="Path to SQLite database file")
    parser.add_argument("--db-host", help="PostgreSQL database host")
    parser.add_argument("--db-port", type=int, help="PostgreSQL database port")
    parser.add_argument("--db-name", help="PostgreSQL database name")
    parser.add_argument("--db-user", help="PostgreSQL database user")
    parser.add_argument("--db-password", help="PostgreSQL database password")

    # Dashboard parameters
    parser.add_argument("--project-key", required=True, help="Zephyr project key")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument(
        "--refresh", type=int, default=10, help="Dashboard refresh interval in seconds",
    )
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    args = parser.parse_args()

    # Create dashboard templates
    create_dashboard_templates()

    # Check environment variables for database connection if not provided as arguments
    if args.db_type == "postgresql":
        args.db_host = args.db_host or os.environ.get("ZTOQ_DB_HOST")
        args.db_port = args.db_port or int(os.environ.get("ZTOQ_DB_PORT", "5432"))
        args.db_name = args.db_name or os.environ.get("ZTOQ_DB_NAME")
        args.db_user = args.db_user or os.environ.get("ZTOQ_DB_USER")
        args.db_password = args.db_password or os.environ.get("ZTOQ_DB_PASSWORD")
    else:  # sqlite
        args.db_path = args.db_path or os.environ.get("ZTOQ_DB_PATH", "ztoq_data.db")

    # Create database URL
    try:
        global db_url, project_key, refresh_interval
        db_url = parse_db_url(
            db_type=args.db_type,
            host=args.db_host,
            port=args.db_port,
            name=args.db_name,
            user=args.db_user,
            password=args.db_password,
            path=args.db_path,
        )
        project_key = args.project_key
        refresh_interval = args.refresh
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
        sys.exit(1)

    # Start the web server
    console.print(f"Starting migration dashboard on http://localhost:{args.port}")
    console.print(f"Project: [bold]{project_key}[/bold], Refresh: {refresh_interval} seconds")

    app.run(host="0.0.0.0", port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
