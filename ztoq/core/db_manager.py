"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
SQLAlchemy-based database manager for handling SQL database operations.

This module provides a more robust SQLAlchemy-based implementation of database operations
for storing and retrieving test data. It supports both SQLite and PostgreSQL databases
and includes features like connection pooling, transaction management, and future
compatibility with Snowflake.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Type, TypeVar, Union, cast
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
import os
import uuid

from sqlalchemy import create_engine, Engine, inspect, func, select, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.ext.declarative import DeclarativeMeta

import pandas as pd
import numpy as np

from ztoq.core.db_models import (
    Base, Project, Folder, Status, Priority, Environment, Label,
    CustomFieldDefinition, CustomFieldValue, Link, Attachment, ScriptFile,
    CaseVersion, TestStep, TestCase, TestCycle, TestPlan, TestExecution,
    MigrationState, EntityBatchState, EntityType
)
from ztoq.models import (
    Project as ProjectModel,
    Folder as FolderModel,
    Status as StatusModel,
    Priority as PriorityModel,
    Environment as EnvironmentModel,
    Case as CaseModel,
    CycleInfo as CycleInfoModel,
    Plan as PlanModel,
    Execution as ExecutionModel,
    CustomField as CustomFieldModel,
    Link as LinkModel,
    Attachment as AttachmentModel,
    CaseStep as CaseStepModel
)
from ztoq.data_fetcher import FetchResult

logger = logging.getLogger(__name__)

# Type variable for ORM models
T = TypeVar('T', bound=Base)


class DatabaseConfig:
    """Configuration for database connections."""
    
    def __init__(
        self,
        db_type: str = "sqlite",
        db_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ):
        """
        Initialize database configuration.
        
        Args:
            db_type: Database type ("sqlite", "postgresql")
            db_path: Path to SQLite database file (for SQLite)
            host: Database host (for PostgreSQL)
            port: Database port (for PostgreSQL)
            username: Database username (for PostgreSQL)
            password: Database password (for PostgreSQL)
            database: Database name (for PostgreSQL)
            pool_size: Connection pool size
            max_overflow: Maximum number of connections to overflow
            echo: Whether to echo SQL statements
        """
        self.db_type = db_type.lower()
        self.db_path = db_path
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.echo = echo
        
        # Create default path for SQLite if not provided
        if self.db_type == "sqlite" and not self.db_path:
            self.db_path = os.path.join(
                os.getcwd(), "ztoq_data.db"
            )
        
    def get_connection_string(self) -> str:
        """
        Get the database connection string based on the configuration.
        
        Returns:
            Database connection string for SQLAlchemy
        """
        if self.db_type == "sqlite":
            db_path = Path(self.db_path) if self.db_path else Path("ztoq_data.db")
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
        elif self.db_type == "postgresql":
            # Validate required PostgreSQL parameters
            if not all([self.host, self.username, self.database]):
                raise ValueError(
                    "Host, username, and database name are required for PostgreSQL"
                )
            port = self.port or 5432
            password_part = f":{self.password}" if self.password else ""
            return f"postgresql://{self.username}{password_part}@{self.host}:{port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


class SQLDatabaseManager:
    """
    SQLAlchemy-based database manager for SQL operations.
    
    This class provides methods for managing database connections, schema, and operations
    using SQLAlchemy ORM. It supports both SQLite and PostgreSQL databases.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the database manager.
        
        Args:
            config: Database configuration
        """
        self.config = config or DatabaseConfig()
        self._engine = self._create_engine()
        self._session_factory = sessionmaker(bind=self._engine)
        self._scoped_session = scoped_session(self._session_factory)
        
    def _create_engine(self) -> Engine:
        """
        Create a SQLAlchemy engine based on the configuration.
        
        Returns:
            SQLAlchemy engine
        """
        conn_str = self.config.get_connection_string()
        engine_kwargs = {
            "echo": self.config.echo,
        }
        
        # Use connection pooling for PostgreSQL
        if self.config.db_type == "postgresql":
            engine_kwargs.update({
                "poolclass": QueuePool,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_pre_ping": True,  # Verify connections before using them
                "pool_recycle": 3600,  # Recycle connections every hour
            })
        
        return create_engine(conn_str, **engine_kwargs)
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        
        This ensures that sessions are properly closed after use,
        even if an error occurs.
        
        Yields:
            SQLAlchemy session object
        """
        session = self._scoped_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
            
    def initialize_database(self) -> None:
        """
        Create all database tables if they don't exist.
        
        This method creates the schema for storing all test data.
        """
        try:
            logger.info("Initializing database schema...")
            Base.metadata.create_all(self._engine)
            logger.info("Database schema initialized successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
    
    def drop_all_tables(self) -> None:
        """
        Drop all tables from the database.
        
        WARNING: This will delete all data in the database.
        """
        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(self._engine)
            logger.warning("All database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def get_or_create(
        self, session: Session, model: Type[T], create_kwargs: Dict[str, Any], **kwargs
    ) -> Tuple[T, bool]:
        """
        Get an existing database object or create if it doesn't exist.
        
        Args:
            session: SQLAlchemy session
            model: Model class
            create_kwargs: Arguments to use when creating a new instance
            **kwargs: Filter arguments to find existing instance
            
        Returns:
            Tuple of (instance, created) where created is True if a new instance was created
        """
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            instance = model(**create_kwargs)
            try:
                session.add(instance)
                session.flush()  # Flush to get the ID
                return instance, True
            except IntegrityError:
                session.rollback()
                # Try again (race condition handling)
                instance = session.query(model).filter_by(**kwargs).first()
                if instance:
                    return instance, False
                else:
                    raise
    
    def save_project(self, project_model: ProjectModel) -> None:
        """
        Save a project to the database.
        
        Args:
            project_model: Project model instance
        """
        with self.get_session() as session:
            project = Project(
                id=project_model.id,
                key=project_model.key,
                name=project_model.name,
                description=project_model.description,
            )
            
            # Get or create the project
            try:
                existing_project = session.query(Project).filter_by(id=project.id).first()
                if existing_project:
                    # Update existing project
                    existing_project.key = project.key
                    existing_project.name = project.name
                    existing_project.description = project.description
                else:
                    session.add(project)
            except SQLAlchemyError as e:
                logger.error(f"Error saving project {project.key}: {e}")
                raise
    
    def save_folder(self, folder_model: FolderModel, project_key: str) -> None:
        """
        Save a folder to the database.
        
        Args:
            folder_model: Folder model instance
            project_key: Project key the folder belongs to
        """
        with self.get_session() as session:
            folder = Folder(
                id=folder_model.id,
                name=folder_model.name,
                folder_type=folder_model.folder_type,
                parent_id=folder_model.parent_id,
                project_key=project_key,
            )
            
            try:
                existing_folder = session.query(Folder).filter_by(id=folder.id).first()
                if existing_folder:
                    # Update existing folder
                    existing_folder.name = folder.name
                    existing_folder.folder_type = folder.folder_type
                    existing_folder.parent_id = folder.parent_id
                    existing_folder.project_key = folder.project_key
                else:
                    session.add(folder)
            except SQLAlchemyError as e:
                logger.error(f"Error saving folder {folder.name}: {e}")
                raise
    
    def save_status(self, status_model: StatusModel, project_key: str) -> None:
        """
        Save a status to the database.
        
        Args:
            status_model: Status model instance
            project_key: Project key the status belongs to
        """
        with self.get_session() as session:
            status = Status(
                id=status_model.id,
                name=status_model.name,
                description=status_model.description,
                color=status_model.color,
                type=status_model.type,
                project_key=project_key,
            )
            
            try:
                existing_status = session.query(Status).filter_by(id=status.id).first()
                if existing_status:
                    # Update existing status
                    existing_status.name = status.name
                    existing_status.description = status.description
                    existing_status.color = status.color
                    existing_status.type = status.type
                    existing_status.project_key = status.project_key
                else:
                    session.add(status)
            except SQLAlchemyError as e:
                logger.error(f"Error saving status {status.name}: {e}")
                raise
    
    def save_priority(self, priority_model: PriorityModel, project_key: str) -> None:
        """
        Save a priority to the database.
        
        Args:
            priority_model: Priority model instance
            project_key: Project key the priority belongs to
        """
        with self.get_session() as session:
            priority = Priority(
                id=priority_model.id,
                name=priority_model.name,
                description=priority_model.description,
                color=priority_model.color,
                rank=priority_model.rank,
                project_key=project_key,
            )
            
            try:
                existing_priority = session.query(Priority).filter_by(id=priority.id).first()
                if existing_priority:
                    # Update existing priority
                    existing_priority.name = priority.name
                    existing_priority.description = priority.description
                    existing_priority.color = priority.color
                    existing_priority.rank = priority.rank
                    existing_priority.project_key = priority.project_key
                else:
                    session.add(priority)
            except SQLAlchemyError as e:
                logger.error(f"Error saving priority {priority.name}: {e}")
                raise
    
    def save_environment(self, environment_model: EnvironmentModel, project_key: str) -> None:
        """
        Save an environment to the database.
        
        Args:
            environment_model: Environment model instance
            project_key: Project key the environment belongs to
        """
        with self.get_session() as session:
            environment = Environment(
                id=environment_model.id,
                name=environment_model.name,
                description=environment_model.description,
                project_key=project_key,
            )
            
            try:
                existing_env = session.query(Environment).filter_by(id=environment.id).first()
                if existing_env:
                    # Update existing environment
                    existing_env.name = environment.name
                    existing_env.description = environment.description
                    existing_env.project_key = environment.project_key
                else:
                    session.add(environment)
            except SQLAlchemyError as e:
                logger.error(f"Error saving environment {environment.name}: {e}")
                raise
    
    def _save_custom_fields(
        self, 
        session: Session, 
        custom_fields: List[CustomFieldModel], 
        entity_type: EntityType, 
        entity_id: str,
        project_key: str
    ) -> None:
        """
        Save custom fields for an entity.
        
        Args:
            session: Database session
            custom_fields: List of custom field models
            entity_type: Type of entity the custom fields belong to
            entity_id: ID of the entity
            project_key: Project key
        """
        for cf in custom_fields:
            # Get or create the custom field definition
            field_def, _ = self.get_or_create(
                session, 
                CustomFieldDefinition,
                create_kwargs={
                    "id": cf.id,
                    "name": cf.name,
                    "type": cf.type,
                    "project_key": project_key,
                },
                id=cf.id,
            )
            
            # Determine value type based on field type
            value_text = None
            value_numeric = None
            value_boolean = None
            value_date = None
            value_json = None
            
            if cf.type in ["text", "paragraph", "radio", "dropdown", "url", "user", "userGroup"]:
                value_text = str(cf.value) if cf.value is not None else None
            elif cf.type in ["numeric"]:
                value_numeric = float(cf.value) if cf.value is not None else None
            elif cf.type in ["checkbox"]:
                value_boolean = bool(cf.value) if cf.value is not None else None
            elif cf.type in ["date", "datetime"]:
                if isinstance(cf.value, datetime):
                    value_date = cf.value
                elif isinstance(cf.value, str):
                    try:
                        value_date = datetime.fromisoformat(cf.value)
                    except ValueError:
                        value_text = cf.value
                else:
                    value_text = str(cf.value) if cf.value is not None else None
            elif cf.type in ["multipleSelect", "table", "hierarchicalSelect", "label", "sprint", "version", "component"]:
                value_json = json.dumps(cf.value) if cf.value is not None else None
            else:
                # Default to text for unknown types
                value_text = str(cf.value) if cf.value is not None else None
            
            # Create a unique ID for the value
            value_id = str(uuid.uuid4())
            
            # Create or update the custom field value
            existing_value = session.query(CustomFieldValue).filter_by(
                field_id=field_def.id,
                entity_type=entity_type,
                entity_id=entity_id
            ).first()
            
            if existing_value:
                existing_value.value_text = value_text
                existing_value.value_numeric = value_numeric
                existing_value.value_boolean = value_boolean
                existing_value.value_date = value_date
                existing_value.value_json = value_json
            else:
                cf_value = CustomFieldValue(
                    id=value_id,
                    field_id=field_def.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    value_text=value_text,
                    value_numeric=value_numeric,
                    value_boolean=value_boolean,
                    value_date=value_date,
                    value_json=value_json,
                )
                session.add(cf_value)
    
    def _save_links(
        self, 
        session: Session, 
        links: List[LinkModel], 
        entity_type: EntityType, 
        entity_id: str
    ) -> None:
        """
        Save links for an entity.
        
        Args:
            session: Database session
            links: List of link models
            entity_type: Type of entity the links belong to
            entity_id: ID of the entity
        """
        # Delete existing links for this entity
        session.query(Link).filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).delete()
        
        # Add new links
        for link in links:
            link_id = link.id or str(uuid.uuid4())
            db_link = Link(
                id=link_id,
                name=link.name,
                url=link.url,
                description=link.description,
                type=link.type,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            session.add(db_link)
    
    def _save_attachments(
        self, 
        session: Session, 
        attachments: List[AttachmentModel], 
        entity_type: EntityType, 
        entity_id: str
    ) -> None:
        """
        Save attachments for an entity.
        
        Args:
            session: Database session
            attachments: List of attachment models
            entity_type: Type of entity the attachments belong to
            entity_id: ID of the entity
        """
        for attachment in attachments:
            attachment_id = attachment.id or str(uuid.uuid4())
            
            # Convert base64 content to binary if present
            content = None
            if attachment.content:
                import base64
                try:
                    content = base64.b64decode(attachment.content)
                except Exception as e:
                    logger.error(f"Error decoding attachment content: {e}")
            
            # Check if attachment already exists
            existing_attachment = session.query(Attachment).filter_by(
                id=attachment_id,
                entity_type=entity_type,
                entity_id=entity_id
            ).first()
            
            if existing_attachment:
                # Update existing attachment
                existing_attachment.filename = attachment.filename
                existing_attachment.content_type = attachment.content_type
                existing_attachment.size = attachment.size
                if content:
                    existing_attachment.content = content
            else:
                # Create new attachment
                db_attachment = Attachment(
                    id=attachment_id,
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                    size=attachment.size,
                    created_on=attachment.created_on,
                    created_by=attachment.created_by,
                    content=content,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                session.add(db_attachment)
    
    def _get_or_create_labels(
        self, session: Session, labels: List[str]
    ) -> List[Label]:
        """
        Get or create labels in the database.
        
        Args:
            session: Database session
            labels: List of label names
            
        Returns:
            List of Label objects
        """
        result = []
        for label_name in labels:
            label, _ = self.get_or_create(
                session,
                Label,
                create_kwargs={"id": str(uuid.uuid4()), "name": label_name},
                name=label_name,
            )
            result.append(label)
        return result
    
    def save_test_case(self, test_case_model: CaseModel, project_key: str) -> None:
        """
        Save a test case to the database.
        
        Args:
            test_case_model: Test case model instance
            project_key: Project key the test case belongs to
        """
        with self.get_session() as session:
            # Handle priority reference
            priority_id = None
            if test_case_model.priority:
                if isinstance(test_case_model.priority, dict):
                    priority_id = test_case_model.priority.get("id")
                else:
                    priority_id = test_case_model.priority.id
            
            # Create or update the test case
            test_case = TestCase(
                id=test_case_model.id,
                key=test_case_model.key,
                name=test_case_model.name,
                objective=test_case_model.objective,
                precondition=test_case_model.precondition,
                description=test_case_model.description,
                status=test_case_model.status,
                priority_id=priority_id,
                priority_name=test_case_model.priority_name,
                folder_id=test_case_model.folder,
                folder_name=test_case_model.folder_name,
                owner=test_case_model.owner,
                owner_name=test_case_model.owner_name,
                component=test_case_model.component,
                component_name=test_case_model.component_name,
                created_on=test_case_model.created_on,
                created_by=test_case_model.created_by,
                updated_on=test_case_model.updated_on,
                updated_by=test_case_model.updated_by,
                version=test_case_model.version,
                estimated_time=test_case_model.estimated_time,
                project_key=project_key,
            )
            
            try:
                existing_case = session.query(TestCase).filter_by(id=test_case.id).first()
                
                if existing_case:
                    # Update existing test case fields
                    for key, value in test_case.__dict__.items():
                        if key != '_sa_instance_state':
                            setattr(existing_case, key, value)
                    
                    # Clear existing relationships to rebuild them
                    session.query(TestStep).filter_by(test_case_id=existing_case.id).delete()
                    session.query(ScriptFile).filter_by(test_case_id=existing_case.id).delete()
                    
                    # Remove existing labels and versions
                    existing_case.labels = []
                    existing_case.versions = []
                    
                    test_case = existing_case
                else:
                    session.add(test_case)
                    session.flush()  # Flush to get the ID
                
                # Add labels
                if test_case_model.labels:
                    test_case.labels = self._get_or_create_labels(session, test_case_model.labels)
                
                # Add steps
                for step in test_case_model.steps:
                    test_step = TestStep(
                        id=step.id or str(uuid.uuid4()),
                        index=step.index,
                        description=step.description,
                        expected_result=step.expected_result,
                        data=step.data,
                        actual_result=step.actual_result,
                        status=step.status,
                        test_case_id=test_case.id,
                    )
                    session.add(test_step)
                
                # Add scripts
                for script in test_case_model.scripts:
                    script_file = ScriptFile(
                        id=script.id,
                        filename=script.filename,
                        type=script.type,
                        content=script.content,
                        test_case_id=test_case.id,
                    )
                    session.add(script_file)
                
                # Add versions
                for version in test_case_model.versions:
                    version_obj, _ = self.get_or_create(
                        session,
                        CaseVersion,
                        create_kwargs={
                            "id": version.id,
                            "name": version.name,
                            "description": version.description,
                            "status": version.status,
                            "created_at": version.created_at,
                            "created_by": version.created_by,
                        },
                        id=version.id,
                    )
                    test_case.versions.append(version_obj)
                
                # Add custom fields
                self._save_custom_fields(
                    session, 
                    test_case_model.custom_fields, 
                    EntityType.TEST_CASE,
                    test_case.id,
                    project_key
                )
                
                # Add links
                self._save_links(
                    session, 
                    test_case_model.links, 
                    EntityType.TEST_CASE,
                    test_case.id
                )
                
                # Add attachments
                self._save_attachments(
                    session, 
                    test_case_model.attachments, 
                    EntityType.TEST_CASE,
                    test_case.id
                )
            
            except SQLAlchemyError as e:
                logger.error(f"Error saving test case {test_case.key}: {e}")
                raise
    
    def save_test_cycle(self, test_cycle_model: CycleInfoModel, project_key: str) -> None:
        """
        Save a test cycle to the database.
        
        Args:
            test_cycle_model: Test cycle model instance
            project_key: Project key the test cycle belongs to
        """
        with self.get_session() as session:
            # Create or update the test cycle
            test_cycle = TestCycle(
                id=test_cycle_model.id,
                key=test_cycle_model.key,
                name=test_cycle_model.name,
                description=test_cycle_model.description,
                status=test_cycle_model.status,
                status_name=test_cycle_model.status_name,
                folder_id=test_cycle_model.folder,
                folder_name=test_cycle_model.folder_name,
                owner=test_cycle_model.owner,
                owner_name=test_cycle_model.owner_name,
                created_on=test_cycle_model.created_on,
                created_by=test_cycle_model.created_by,
                updated_on=test_cycle_model.updated_on,
                updated_by=test_cycle_model.updated_by,
                project_key=project_key,
            )
            
            try:
                existing_cycle = session.query(TestCycle).filter_by(id=test_cycle.id).first()
                
                if existing_cycle:
                    # Update existing test cycle fields
                    for key, value in test_cycle.__dict__.items():
                        if key != '_sa_instance_state':
                            setattr(existing_cycle, key, value)
                    
                    test_cycle = existing_cycle
                else:
                    session.add(test_cycle)
                    session.flush()  # Flush to get the ID
                
                # Add custom fields
                self._save_custom_fields(
                    session, 
                    test_cycle_model.custom_fields, 
                    EntityType.TEST_CYCLE,
                    test_cycle.id,
                    project_key
                )
                
                # Add links
                self._save_links(
                    session, 
                    test_cycle_model.links, 
                    EntityType.TEST_CYCLE,
                    test_cycle.id
                )
                
                # Add attachments
                self._save_attachments(
                    session, 
                    test_cycle_model.attachments, 
                    EntityType.TEST_CYCLE,
                    test_cycle.id
                )
            
            except SQLAlchemyError as e:
                logger.error(f"Error saving test cycle {test_cycle.key}: {e}")
                raise
    
    def save_test_execution(self, test_execution_model: ExecutionModel, project_key: str) -> None:
        """
        Save a test execution to the database.
        
        Args:
            test_execution_model: Test execution model instance
            project_key: Project key the test execution belongs to
        """
        with self.get_session() as session:
            # Create or update the test execution
            test_execution = TestExecution(
                id=test_execution_model.id,
                test_case_key=test_execution_model.test_case_key,
                cycle_id=test_execution_model.cycle_id,
                cycle_name=test_execution_model.cycle_name,
                status=test_execution_model.status,
                status_name=test_execution_model.status_name,
                environment_id=test_execution_model.environment,
                environment_name=test_execution_model.environment_name,
                executed_by=test_execution_model.executed_by,
                executed_by_name=test_execution_model.executed_by_name,
                executed_on=test_execution_model.executed_on,
                created_on=test_execution_model.created_on,
                created_by=test_execution_model.created_by,
                updated_on=test_execution_model.updated_on,
                updated_by=test_execution_model.updated_by,
                actual_time=test_execution_model.actual_time,
                comment=test_execution_model.comment,
                project_key=project_key,
            )
            
            try:
                existing_execution = session.query(TestExecution).filter_by(id=test_execution.id).first()
                
                if existing_execution:
                    # Update existing test execution fields
                    for key, value in test_execution.__dict__.items():
                        if key != '_sa_instance_state':
                            setattr(existing_execution, key, value)
                    
                    # Clear existing steps to rebuild them
                    session.query(TestStep).filter_by(test_execution_id=existing_execution.id).delete()
                    
                    test_execution = existing_execution
                else:
                    session.add(test_execution)
                    session.flush()  # Flush to get the ID
                
                # Add steps
                for step in test_execution_model.steps:
                    execution_step = TestStep(
                        id=step.id or str(uuid.uuid4()),
                        index=step.index,
                        description=step.description,
                        expected_result=step.expected_result,
                        data=step.data,
                        actual_result=step.actual_result,
                        status=step.status,
                        test_execution_id=test_execution.id,
                    )
                    session.add(execution_step)
                
                # Add custom fields
                self._save_custom_fields(
                    session, 
                    test_execution_model.custom_fields, 
                    EntityType.TEST_EXECUTION,
                    test_execution.id,
                    project_key
                )
                
                # Add links
                self._save_links(
                    session, 
                    test_execution_model.links, 
                    EntityType.TEST_EXECUTION,
                    test_execution.id
                )
                
                # Add attachments
                self._save_attachments(
                    session, 
                    test_execution_model.attachments, 
                    EntityType.TEST_EXECUTION,
                    test_execution.id
                )
            
            except SQLAlchemyError as e:
                logger.error(f"Error saving test execution {test_execution.id}: {e}")
                raise
    
    def save_project_data(
        self, project_key: str, fetch_results: Dict[str, FetchResult]
    ) -> Dict[str, int]:
        """
        Save all fetched data for a project.
        
        This method coordinates saving different entity types to their respective tables.
        It handles the relationships between entities and ensures proper insertion order.
        
        Args:
            project_key: The project key
            fetch_results: Dictionary of fetched data results
            
        Returns:
            Dictionary with counts of inserted records by entity type
        """
        counts = {}
        
        # Save project first if available
        # This is usually fetched separately, so we may need to create a placeholder
        if "project" in fetch_results:
            project_result = fetch_results["project"]
            if project_result.success and project_result.items:
                self.save_project(project_result.items[0])
                counts["project"] = 1
        else:
            # Create a minimal project entry to satisfy foreign key constraints
            with self.get_session() as session:
                project, created = self.get_or_create(
                    session,
                    Project,
                    create_kwargs={
                        "id": f"placeholder_{project_key}",
                        "key": project_key,
                        "name": f"Project {project_key}",
                        "description": f"Placeholder project for {project_key}",
                    },
                    key=project_key,
                )
                if created:
                    counts["project"] = 1
                else:
                    counts["project"] = 0
        
        # Save different entity types in the correct order to satisfy foreign key constraints
        
        # 1. Folders (with self-references)
        if "folders" in fetch_results:
            folder_result = fetch_results["folders"]
            if folder_result.success:
                # Sort folders to handle parent-child relationships
                folders = sorted(folder_result.items, key=lambda f: len(f.id))
                for folder in folders:
                    self.save_folder(folder, project_key)
                counts["folders"] = len(folders)
        
        # 2. Statuses
        if "statuses" in fetch_results:
            status_result = fetch_results["statuses"]
            if status_result.success:
                for status in status_result.items:
                    self.save_status(status, project_key)
                counts["statuses"] = len(status_result.items)
        
        # 3. Priorities
        if "priorities" in fetch_results:
            priority_result = fetch_results["priorities"]
            if priority_result.success:
                for priority in priority_result.items:
                    self.save_priority(priority, project_key)
                counts["priorities"] = len(priority_result.items)
        
        # 4. Environments
        if "environments" in fetch_results:
            environment_result = fetch_results["environments"]
            if environment_result.success:
                for environment in environment_result.items:
                    self.save_environment(environment, project_key)
                counts["environments"] = len(environment_result.items)
        
        # 5. Test cases
        if "test_cases" in fetch_results:
            test_case_result = fetch_results["test_cases"]
            if test_case_result.success:
                for test_case in test_case_result.items:
                    self.save_test_case(test_case, project_key)
                counts["test_cases"] = len(test_case_result.items)
        
        # 6. Test cycles
        if "test_cycles" in fetch_results:
            test_cycle_result = fetch_results["test_cycles"]
            if test_cycle_result.success:
                for test_cycle in test_cycle_result.items:
                    self.save_test_cycle(test_cycle, project_key)
                counts["test_cycles"] = len(test_cycle_result.items)
        
        # 7. Test executions
        if "test_executions" in fetch_results:
            test_execution_result = fetch_results["test_executions"]
            if test_execution_result.success:
                for test_execution in test_execution_result.items:
                    self.save_test_execution(test_execution, project_key)
                counts["test_executions"] = len(test_execution_result.items)
        
        return counts
    
    def save_all_projects_data(
        self, all_projects_data: Dict[str, Dict[str, FetchResult]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Save all fetched data for multiple projects.
        
        Args:
            all_projects_data: Dictionary mapping project keys to their fetch results
            
        Returns:
            Dictionary mapping project keys to counts of inserted records by entity type
        """
        # Initialize database first
        self.initialize_database()
        
        # Save data for each project
        results = {}
        for project_key, project_data in all_projects_data.items():
            results[project_key] = self.save_project_data(project_key, project_data)
        
        return results
    
    def get_migration_state(self, project_key: str) -> Optional[MigrationState]:
        """
        Get the migration state for a project.
        
        Args:
            project_key: Project key
            
        Returns:
            Migration state object or None if not found
        """
        with self.get_session() as session:
            return session.query(MigrationState).filter_by(project_key=project_key).first()
    
    def update_migration_state(
        self, 
        project_key: str, 
        extraction_status: Optional[str] = None,
        transformation_status: Optional[str] = None,
        loading_status: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MigrationState:
        """
        Update the migration state for a project.
        
        Args:
            project_key: Project key
            extraction_status: Status of extraction phase
            transformation_status: Status of transformation phase
            loading_status: Status of loading phase
            error_message: Error message if any
            metadata: Additional metadata as dictionary
            
        Returns:
            Updated migration state object
        """
        with self.get_session() as session:
            state = session.query(MigrationState).filter_by(project_key=project_key).first()
            
            if not state:
                state = MigrationState(
                    project_key=project_key,
                    extraction_status=extraction_status or "not_started",
                    transformation_status=transformation_status or "not_started",
                    loading_status=loading_status or "not_started",
                )
                session.add(state)
            else:
                if extraction_status:
                    state.extraction_status = extraction_status
                if transformation_status:
                    state.transformation_status = transformation_status
                if loading_status:
                    state.loading_status = loading_status
            
            if error_message:
                state.error_message = error_message
            
            if metadata:
                # Update metadata
                current_metadata = state.metadata_dict
                current_metadata.update(metadata)
                state.meta_data = json.dumps(current_metadata)
            
            state.last_updated = datetime.utcnow()
            return state
    
    def create_entity_batch_state(
        self,
        project_key: str,
        entity_type: str,
        batch_number: int,
        total_batches: Optional[int] = None,
        items_count: Optional[int] = None,
        status: str = "not_started"
    ) -> EntityBatchState:
        """
        Create a new entity batch state record.
        
        Args:
            project_key: Project key
            entity_type: Type of entity ("test_case", "test_cycle", etc.)
            batch_number: Batch number
            total_batches: Total number of batches
            items_count: Number of items in this batch
            status: Initial status
            
        Returns:
            Created entity batch state object
        """
        with self.get_session() as session:
            # Check if batch already exists
            batch = session.query(EntityBatchState).filter_by(
                project_key=project_key,
                entity_type=entity_type,
                batch_number=batch_number
            ).first()
            
            if batch:
                # Update existing batch
                batch.total_batches = total_batches or batch.total_batches
                batch.items_count = items_count or batch.items_count
                batch.status = status
                batch.started_at = datetime.utcnow() if status == "in_progress" else batch.started_at
                batch.last_updated = datetime.utcnow()
            else:
                # Create new batch
                batch = EntityBatchState(
                    project_key=project_key,
                    entity_type=entity_type,
                    batch_number=batch_number,
                    total_batches=total_batches,
                    items_count=items_count,
                    status=status,
                    started_at=datetime.utcnow() if status == "in_progress" else None,
                    last_updated=datetime.utcnow()
                )
                session.add(batch)
            
            return batch
    
    def update_entity_batch_state(
        self,
        project_key: str,
        entity_type: str,
        batch_number: int,
        status: Optional[str] = None,
        processed_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[EntityBatchState]:
        """
        Update an entity batch state record.
        
        Args:
            project_key: Project key
            entity_type: Type of entity
            batch_number: Batch number
            status: Updated status
            processed_count: Number of processed items
            error_message: Error message if any
            
        Returns:
            Updated entity batch state object or None if not found
        """
        with self.get_session() as session:
            batch = session.query(EntityBatchState).filter_by(
                project_key=project_key,
                entity_type=entity_type,
                batch_number=batch_number
            ).first()
            
            if not batch:
                return None
            
            if status:
                batch.status = status
                if status == "completed":
                    batch.completed_at = datetime.utcnow()
            
            if processed_count is not None:
                batch.processed_count = processed_count
            
            if error_message:
                batch.error_message = error_message
            
            batch.last_updated = datetime.utcnow()
            return batch
    
    def get_incomplete_batches(
        self, project_key: str, entity_type: Optional[str] = None
    ) -> List[EntityBatchState]:
        """
        Get all incomplete entity batches for a project.
        
        Args:
            project_key: Project key
            entity_type: Optional entity type filter
            
        Returns:
            List of incomplete entity batch state objects
        """
        with self.get_session() as session:
            query = session.query(EntityBatchState).filter(
                EntityBatchState.project_key == project_key,
                EntityBatchState.status.in_(["not_started", "in_progress", "failed"])
            )
            
            if entity_type:
                query = query.filter(EntityBatchState.entity_type == entity_type)
            
            return query.order_by(
                EntityBatchState.entity_type,
                EntityBatchState.batch_number
            ).all()
    
    def get_statistics(self, project_key: str) -> Dict[str, int]:
        """
        Get statistics for a project.
        
        Args:
            project_key: Project key
            
        Returns:
            Dictionary with counts of entities by type
        """
        with self.get_session() as session:
            stats = {}
            
            # Projects
            stats["projects"] = session.query(Project).filter_by(key=project_key).count()
            
            # Folders
            stats["folders"] = session.query(Folder).filter_by(project_key=project_key).count()
            
            # Statuses
            stats["statuses"] = session.query(Status).filter_by(project_key=project_key).count()
            
            # Priorities
            stats["priorities"] = session.query(Priority).filter_by(project_key=project_key).count()
            
            # Environments
            stats["environments"] = session.query(Environment).filter_by(project_key=project_key).count()
            
            # Test cases
            stats["test_cases"] = session.query(TestCase).filter_by(project_key=project_key).count()
            
            # Test cycles
            stats["test_cycles"] = session.query(TestCycle).filter_by(project_key=project_key).count()
            
            # Test plans
            stats["test_plans"] = session.query(TestPlan).filter_by(project_key=project_key).count()
            
            # Test executions
            stats["test_executions"] = session.query(TestExecution).filter_by(project_key=project_key).count()
            
            # Test steps (from cases)
            stats["test_steps"] = session.query(TestStep).join(
                TestCase, TestStep.test_case_id == TestCase.id
            ).filter(
                TestCase.project_key == project_key
            ).count()
            
            # Custom fields
            stats["custom_fields"] = session.query(CustomFieldValue).join(
                CustomFieldDefinition, 
                CustomFieldValue.field_id == CustomFieldDefinition.id
            ).filter(
                CustomFieldDefinition.project_key == project_key
            ).count()
            
            # Attachments
            stats["attachments"] = session.query(Attachment).filter(
                Attachment.entity_id.in_(
                    # Entities from this project
                    session.query(TestCase.id).filter_by(project_key=project_key).union(
                        session.query(TestCycle.id).filter_by(project_key=project_key)
                    ).union(
                        session.query(TestExecution.id).filter_by(project_key=project_key)
                    )
                )
            ).count()
            
            return stats
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries with query results
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            
            # Convert result proxy to list of dictionaries
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def query_to_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        This is useful for complex data transformations using pandas.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Pandas DataFrame with query results
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            
            # Convert result proxy to DataFrame
            columns = result.keys()
            data = result.fetchall()
            
            # Create DataFrame
            return pd.DataFrame(data, columns=columns)