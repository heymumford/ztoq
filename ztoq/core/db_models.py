"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
SQLAlchemy ORM models for the SQL database implementation.

This module defines all database entities using SQLAlchemy ORM models.
These models represent the structure of the database tables and their relationships.
"""

import enum
import json
from datetime import datetime
from typing import Any
from sqlalchemy import (
    Boolean,
        Column,
        DateTime,
        Enum,
        Float,
        ForeignKey,
        Index,
        Integer,
        JSON,
        LargeBinary,
        String,
        Table,
        Text,
        UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class EntityType(enum.Enum):
    """Types of entities that can be referenced by attachments, etc."""

    TEST_CASE = "TEST_CASE"
    TEST_EXECUTION = "TEST_EXECUTION"
    TEST_STEP = "TEST_STEP"
    TEST_CYCLE = "TEST_CYCLE"
    TEST_PLAN = "TEST_PLAN"
    FOLDER = "FOLDER"


# Association tables for many-to-many relationships
case_label_association = Table(
    "case_label_association",
        Base.metadata,
        Column("test_case_id", String(50), ForeignKey("test_cases.id", ondelete="CASCADE")),
        Column("label_id", String(50), ForeignKey("labels.id", ondelete="CASCADE")),
        Index("idx_case_label", "test_case_id", "label_id"),
)

case_version_association = Table(
    "case_version_association",
        Base.metadata,
        Column("test_case_id", String(50), ForeignKey("test_cases.id", ondelete="CASCADE")),
        Column("version_id", String(50), ForeignKey("case_versions.id", ondelete="CASCADE")),
        Index("idx_case_version", "test_case_id", "version_id"),
)


class Project(Base):
    """Project entity model."""

    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Relationships
    folders = relationship("Folder", back_populates="project", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    test_cycles = relationship("TestCycle", back_populates="project", cascade="all, delete-orphan")
    test_plans = relationship("TestPlan", back_populates="project", cascade="all, delete-orphan")
    statuses = relationship("Status", back_populates="project", cascade="all, delete-orphan")
    priorities = relationship("Priority", back_populates="project", cascade="all, delete-orphan")
    environments = relationship(
        "Environment", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(key='{self.key}', name='{self.name}')>"


class Folder(Base):
    """Folder entity model."""

    __tablename__ = "folders"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    folder_type = Column(String(50), nullable=False)  # "TEST_CASE", "TEST_CYCLE", "TEST_PLAN"
    parent_id = Column(String(50), ForeignKey("folders.id", ondelete="SET NULL"))
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], backref="children")
    test_cases = relationship("TestCase", back_populates="folder")
    test_cycles = relationship("TestCycle", back_populates="folder")
    test_plans = relationship("TestPlan", back_populates="folder")

    # Indexes
    __table_args__ = (
        Index("idx_folder_project", "project_key"),
            Index("idx_folder_parent", "parent_id"),
        )

    def __repr__(self):
        return f"<Folder(id='{self.id}', name='{self.name}', type='{self.folder_type}')>"


class Status(Base):
    """Status entity model."""

    __tablename__ = "statuses"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(20))
    type = Column(String(50), nullable=False)  # "TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION"
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="statuses")

    # Indexes
    __table_args__ = (Index("idx_status_project", "project_key"), Index("idx_status_type", "type"))

    def __repr__(self):
        return f"<Status(name='{self.name}', type='{self.type}')>"


class Priority(Base):
    """Priority entity model."""

    __tablename__ = "priorities"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(20))
    rank = Column(Integer, nullable=False)
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="priorities")
    test_cases = relationship("TestCase", back_populates="priority")

    # Indexes
    __table_args__ = (
        Index("idx_priority_project", "project_key"),
            Index("idx_priority_rank", "rank"),
        )

    def __repr__(self):
        return f"<Priority(name='{self.name}', rank={self.rank})>"


class Environment(Base):
    """Environment entity model."""

    __tablename__ = "environments"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="environments")
    test_executions = relationship("TestExecution", back_populates="environment")

    # Indexes
    __table_args__ = (Index("idx_environment_project", "project_key"),)

    def __repr__(self):
        return f"<Environment(name='{self.name}')>"


class Label(Base):
    """Label entity model."""

    __tablename__ = "labels"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)

    # Relationships - many-to-many with test cases
    test_cases = relationship("TestCase", secondary=case_label_association, back_populates="labels")

    def __repr__(self):
        return f"<Label(name='{self.name}')>"


class CustomFieldDefinition(Base):
    """Custom field definition entity model."""

    __tablename__ = "custom_field_definitions"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # text, paragraph, checkbox, etc.
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project")
    values = relationship(
        "CustomFieldValue", back_populates="field_definition", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_custom_field_project", "project_key"),)

    def __repr__(self):
        return f"<CustomFieldDefinition(name='{self.name}', type='{self.type}')>"


class CustomFieldValue(Base):
    """Custom field value entity model."""

    __tablename__ = "custom_field_values"

    id = Column(String(50), primary_key=True)
    field_id = Column(
        String(50), ForeignKey("custom_field_definitions.id", ondelete="CASCADE"), nullable=False
    )
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(String(50), nullable=False)
    value_text = Column(Text)
    value_numeric = Column(Float)
    value_boolean = Column(Boolean)
    value_date = Column(DateTime)
    value_json = Column(Text)  # For arrays, objects, etc.

    # Relationships
    field_definition = relationship("CustomFieldDefinition", back_populates="values")

    # Indexes
    __table_args__ = (
        Index("idx_custom_field_value_entity", "entity_type", "entity_id"),
            Index("idx_custom_field_value_field", "field_id"),
        )

    def __repr__(self):
        return f"<CustomFieldValue(field_id='{self.field_id}', entity='{self.entity_type.value}:{self.entity_id}')>"


class Link(Base):
    """Link entity model."""

    __tablename__ = "links"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2000), nullable=False)
    description = Column(Text)
    type = Column(String(50), nullable=False)  # "issue", "web", "testCycle"
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(String(50), nullable=False)

    # Indexes
    __table_args__ = (Index("idx_link_entity", "entity_type", "entity_id"),)

    def __repr__(self):
        return f"<Link(name='{self.name}', type='{self.type}')>"


class Attachment(Base):
    """Attachment entity model."""

    __tablename__ = "attachments"

    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer)
    created_on = Column(DateTime)
    created_by = Column(String(100))
    content = Column(LargeBinary)  # Binary data
    content_url = Column(String(2000))  # Original URL if available
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(String(50), nullable=False)

    # Indexes
    __table_args__ = (Index("idx_attachment_entity", "entity_type", "entity_id"),)

    def __repr__(self):
        return f"<Attachment(filename='{self.filename}', entity='{self.entity_type.value}:{self.entity_id}')>"


class ScriptFile(Base):
    """Script file entity model."""

    __tablename__ = "script_files"

    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # cucumber, python, javascript, etc.
    content = Column(Text)
    test_case_id = Column(
        String(50), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    test_case = relationship("TestCase", back_populates="scripts")

    # Indexes
    __table_args__ = (Index("idx_script_test_case", "test_case_id"),)

    def __repr__(self):
        return f"<ScriptFile(filename='{self.filename}', type='{self.type}')>"


class CaseVersion(Base):
    """Test case version entity model."""

    __tablename__ = "case_versions"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    created_by = Column(String(100))

    # Relationships - many-to-many with test cases
    test_cases = relationship(
        "TestCase", secondary=case_version_association, back_populates="versions"
    )

    def __repr__(self):
        return f"<CaseVersion(name='{self.name}', created_at='{self.created_at}')>"


class TestStep(Base):
    """Test step entity model."""

    __tablename__ = "test_steps"

    id = Column(String(50), primary_key=True)
    index = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    expected_result = Column(Text)
    data = Column(Text)
    actual_result = Column(Text)
    status = Column(String(50))
    test_case_id = Column(
        String(50), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=True
    )
    test_execution_id = Column(
        String(50), ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    test_case = relationship("TestCase", back_populates="steps", foreign_keys=[test_case_id])
    test_execution = relationship(
        "TestExecution", back_populates="steps", foreign_keys=[test_execution_id]
    )

    # Indexes
    __table_args__ = (
        Index("idx_step_test_case", "test_case_id"),
            Index("idx_step_test_execution", "test_execution_id"),
            Index("idx_step_index", "index"),
        )

    def __repr__(self):
        return f"<TestStep(index={self.index}, description='{self.description[:20]}...')>"


class TestCase(Base):
    """Test case entity model."""

    __tablename__ = "test_cases"

    id = Column(String(50), primary_key=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    objective = Column(Text)
    precondition = Column(Text)
    description = Column(Text)
    status = Column(String(50))
    priority_id = Column(String(50), ForeignKey("priorities.id", ondelete="SET NULL"))
    priority_name = Column(String(100))
    folder_id = Column(String(50), ForeignKey("folders.id", ondelete="SET NULL"))
    folder_name = Column(String(255))
    owner = Column(String(100))
    owner_name = Column(String(255))
    component = Column(String(100))
    component_name = Column(String(255))
    created_on = Column(DateTime)
    created_by = Column(String(100))
    updated_on = Column(DateTime)
    updated_by = Column(String(100))
    version = Column(String(50))
    estimated_time = Column(Integer)
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_cases")
    priority = relationship("Priority", back_populates="test_cases")
    folder = relationship("Folder", back_populates="test_cases")
    steps = relationship(
        "TestStep",
            back_populates="test_case",
            foreign_keys=[TestStep.test_case_id],
            cascade="all, delete-orphan",
        )
    scripts = relationship("ScriptFile", back_populates="test_case", cascade="all, delete-orphan")
    executions = relationship("TestExecution", back_populates="test_case")
    labels = relationship("Label", secondary=case_label_association, back_populates="test_cases")
    versions = relationship(
        "CaseVersion", secondary=case_version_association, back_populates="test_cases"
    )

    # Indexes
    __table_args__ = (
        Index("idx_test_case_project", "project_key"),
            Index("idx_test_case_folder", "folder_id"),
            Index("idx_test_case_priority", "priority_id"),
            Index("idx_test_case_status", "status"),
        )

    def __repr__(self):
        return f"<TestCase(key='{self.key}', name='{self.name}')>"

    @property
    def custom_fields(self) -> list[dict[str, Any]]:
        """Get custom fields for this test case from the database."""
        # This would be implemented in the service layer to query CustomFieldValue
        return []

    @property
    def attachments(self) -> list[dict[str, Any]]:
        """Get attachments for this test case from the database."""
        # This would be implemented in the service layer to query Attachment
        return []

    @property
    def links(self) -> list[dict[str, Any]]:
        """Get links for this test case from the database."""
        # This would be implemented in the service layer to query Link
        return []


class TestCycle(Base):
    """Test cycle entity model."""

    __tablename__ = "test_cycles"

    id = Column(String(50), primary_key=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50))
    status_name = Column(String(100))
    folder_id = Column(String(50), ForeignKey("folders.id", ondelete="SET NULL"))
    folder_name = Column(String(255))
    owner = Column(String(100))
    owner_name = Column(String(255))
    created_on = Column(DateTime)
    created_by = Column(String(100))
    updated_on = Column(DateTime)
    updated_by = Column(String(100))
    planned_start_date = Column(DateTime)
    planned_end_date = Column(DateTime)
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_cycles")
    folder = relationship("Folder", back_populates="test_cycles")
    executions = relationship(
        "TestExecution", back_populates="test_cycle", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_test_cycle_project", "project_key"),
            Index("idx_test_cycle_folder", "folder_id"),
            Index("idx_test_cycle_status", "status"),
        )

    def __repr__(self):
        return f"<TestCycle(key='{self.key}', name='{self.name}')>"

    @property
    def custom_fields(self) -> list[dict[str, Any]]:
        """Get custom fields for this test cycle from the database."""
        # This would be implemented in the service layer to query CustomFieldValue
        return []

    @property
    def attachments(self) -> list[dict[str, Any]]:
        """Get attachments for this test cycle from the database."""
        # This would be implemented in the service layer to query Attachment
        return []

    @property
    def links(self) -> list[dict[str, Any]]:
        """Get links for this test cycle from the database."""
        # This would be implemented in the service layer to query Link
        return []


class TestPlan(Base):
    """Test plan entity model."""

    __tablename__ = "test_plans"

    id = Column(String(50), primary_key=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50))
    status_name = Column(String(100))
    folder_id = Column(String(50), ForeignKey("folders.id", ondelete="SET NULL"))
    folder_name = Column(String(255))
    owner = Column(String(100))
    owner_name = Column(String(255))
    created_on = Column(DateTime)
    created_by = Column(String(100))
    updated_on = Column(DateTime)
    updated_by = Column(String(100))
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_plans")
    folder = relationship("Folder", back_populates="test_plans")

    # Indexes
    __table_args__ = (
        Index("idx_test_plan_project", "project_key"),
            Index("idx_test_plan_folder", "folder_id"),
            Index("idx_test_plan_status", "status"),
        )

    def __repr__(self):
        return f"<TestPlan(key='{self.key}', name='{self.name}')>"

    @property
    def custom_fields(self) -> list[dict[str, Any]]:
        """Get custom fields for this test plan from the database."""
        # This would be implemented in the service layer to query CustomFieldValue
        return []

    @property
    def links(self) -> list[dict[str, Any]]:
        """Get links for this test plan from the database."""
        # This would be implemented in the service layer to query Link
        return []


class TestExecution(Base):
    """Test execution entity model."""

    __tablename__ = "test_executions"

    id = Column(String(50), primary_key=True)
    test_case_key = Column(
        String(50), ForeignKey("test_cases.key", ondelete="CASCADE"), nullable=False
    )
    cycle_id = Column(String(50), ForeignKey("test_cycles.id", ondelete="CASCADE"), nullable=False)
    cycle_name = Column(String(255))
    status = Column(String(50), nullable=False)
    status_name = Column(String(100))
    environment_id = Column(String(50), ForeignKey("environments.id", ondelete="SET NULL"))
    environment_name = Column(String(100))
    executed_by = Column(String(100))
    executed_by_name = Column(String(255))
    executed_on = Column(DateTime)
    created_on = Column(DateTime)
    created_by = Column(String(100))
    updated_on = Column(DateTime)
    updated_by = Column(String(100))
    actual_time = Column(Integer)
    comment = Column(Text)
    project_key = Column(String(50), ForeignKey("projects.key", ondelete="CASCADE"), nullable=False)

    # Relationships
    project = relationship("Project")
    test_case = relationship("TestCase", back_populates="executions")
    test_cycle = relationship("TestCycle", back_populates="executions")
    environment = relationship("Environment", back_populates="test_executions")
    steps = relationship(
        "TestStep",
            back_populates="test_execution",
            foreign_keys=[TestStep.test_execution_id],
            cascade="all, delete-orphan",
        )

    # Indexes
    __table_args__ = (
        Index("idx_test_execution_project", "project_key"),
            Index("idx_test_execution_cycle", "cycle_id"),
            Index("idx_test_execution_case", "test_case_key"),
            Index("idx_test_execution_status", "status"),
            Index("idx_test_execution_environment", "environment_id"),
        )

    def __repr__(self):
        return (
            f"<TestExecution(id='{self.id}', case='{self.test_case_key}', status='{self.status}')>"
        )

    @property
    def custom_fields(self) -> list[dict[str, Any]]:
        """Get custom fields for this test execution from the database."""
        # This would be implemented in the service layer to query CustomFieldValue
        return []

    @property
    def attachments(self) -> list[dict[str, Any]]:
        """Get attachments for this test execution from the database."""
        # This would be implemented in the service layer to query Attachment
        return []

    @property
    def links(self) -> list[dict[str, Any]]:
        """Get links for this test execution from the database."""
        # This would be implemented in the service layer to query Link
        return []


# Migration tracking tables


class MigrationState(Base):
    """Migration state tracking."""

    __tablename__ = "migration_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_key = Column(String(50), unique=True, index=True)
    extraction_status = Column(String(50))  # "not_started", "in_progress", "completed", "failed"
    transformation_status = Column(String(50))
    loading_status = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text)
    meta_data = Column(Text)  # JSON data for additional info - renamed from metadata

    def __repr__(self):
        return f"<MigrationState(project='{self.project_key}', extraction='{self.extraction_status}', transformation='{self.transformation_status}', loading='{self.loading_status}')>"

    @property
    def metadata_dict(self) -> dict[str, Any]:
        """Get metadata as a dictionary."""
        if self.meta_data:
            return json.loads(self.meta_data)
        return {}


class RecommendationHistory(Base):
    """Track recommendations made over time for historical analysis."""

    __tablename__ = "recommendation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_key = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    recommendation_id = Column(String(50), nullable=False, index=True)  # Unique ID for each recommendation
    priority = Column(String(10), nullable=False)  # high, medium, low
    category = Column(String(50), nullable=False)
    issue = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    status = Column(String(20), default="open")  # open, implemented, rejected, pending
    implemented_at = Column(DateTime, nullable=True)
    impact_score = Column(Float, nullable=True)  # Optional tracking of recommendation impact
    migration_phase = Column(String(20), nullable=True)  # Which phase of migration it relates to
    entity_type = Column(String(50), nullable=True)  # Which entity type it relates to
    meta_data = Column(JSON, nullable=True)  # Additional context/details

    def __repr__(self):
        return f"<RecommendationHistory(project='{self.project_key}', id='{self.recommendation_id}', priority='{self.priority}', status='{self.status}')>"

    @property
    def metadata_dict(self) -> dict[str, Any]:
        """Get metadata as a dictionary."""
        if self.meta_data:
            return json.loads(self.meta_data)
        return {}


class EntityBatchState(Base):
    """Entity batch processing state tracking."""

    __tablename__ = "entity_batch_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_key = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # "test_case", "test_cycle", etc.
    batch_number = Column(Integer, nullable=False)
    total_batches = Column(Integer)
    items_count = Column(Integer)
    processed_count = Column(Integer, default=0)
    status = Column(String(50))  # "not_started", "in_progress", "completed", "failed"
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text)

    # Unique constraint to ensure we don't have duplicate batch entries
    __table_args__ = (
        UniqueConstraint("project_key", "entity_type", "batch_number", name="uq_entity_batch"),
            Index("idx_entity_batch_project", "project_key"),
            Index("idx_entity_batch_status", "status"),
        )

    def __repr__(self):
        return f"<EntityBatchState(project='{self.project_key}', type='{self.entity_type}', batch={self.batch_number}, status='{self.status}')>"
