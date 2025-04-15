"""
Test data factories for the ZTOQ testing framework.

This module provides base factory classes for generating test data,
following the Factory pattern to make test data creation more
consistent and maintainable.
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

# Type variable for generic factory methods
T = TypeVar("T")


class BaseFactory:
    """
    Base class for all test data factories.

    This class provides common functionality for generating test data,
    including random values and sequences.
    """

    @staticmethod
    def random_string(length: int = 10, prefix: str = "") -> str:
        """
        Generate a random string of the specified length.

        Args:
            length: Length of the string to generate
            prefix: Optional prefix to prepend to the string

        Returns:
            str: Random string
        """
        chars = string.ascii_letters + string.digits
        random_part = "".join(random.choice(chars) for _ in range(length))
        return f"{prefix}{random_part}"

    @staticmethod
    def random_int(min_value: int = 1, max_value: int = 1000) -> int:
        """
        Generate a random integer in the specified range.

        Args:
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)

        Returns:
            int: Random integer
        """
        return random.randint(min_value, max_value)

    @staticmethod
    def random_float(min_value: float = 0.0, max_value: float = 1.0) -> float:
        """
        Generate a random float in the specified range.

        Args:
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)

        Returns:
            float: Random float
        """
        return random.uniform(min_value, max_value)

    @staticmethod
    def random_bool() -> bool:
        """
        Generate a random boolean value.

        Returns:
            bool: Random boolean
        """
        return random.choice([True, False])

    @staticmethod
    def random_date(
        start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> datetime:
        """
        Generate a random date within the specified range.

        Args:
            start_date: Start date (inclusive, defaults to 1 year ago)
            end_date: End date (inclusive, defaults to now)

        Returns:
            datetime: Random date
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return start_date + timedelta(days=random_days)

    @staticmethod
    def random_choice(choices: List[Any]) -> Any:
        """
        Select a random item from a list of choices.

        Args:
            choices: List of items to choose from

        Returns:
            Any: Random item from the list
        """
        return random.choice(choices)

    @staticmethod
    def random_subset(
        items: List[Any], min_size: int = 1, max_size: Optional[int] = None
    ) -> List[Any]:
        """
        Select a random subset of items from a list.

        Args:
            items: List of items to choose from
            min_size: Minimum size of the subset
            max_size: Maximum size of the subset (defaults to length of items)

        Returns:
            List[Any]: Random subset of items
        """
        if max_size is None:
            max_size = len(items)

        size = random.randint(min_size, min(max_size, len(items)))
        return random.sample(items, size)

    @staticmethod
    def random_uuid() -> str:
        """
        Generate a random UUID.

        Returns:
            str: Random UUID as a string
        """
        return str(uuid.uuid4())

    @classmethod
    def create(cls, **kwargs: Any) -> Any:
        """
        Create a single instance of the factory's data type.

        This is a placeholder that should be overridden by subclasses.

        Args:
            **kwargs: Attributes to override default values

        Returns:
            Any: Created instance
        """
        raise NotImplementedError("Subclasses must implement create()")

    @classmethod
    def create_batch(cls, size: int, **kwargs: Any) -> List[Any]:
        """
        Create multiple instances of the factory's data type.

        Args:
            size: Number of instances to create
            **kwargs: Attributes to override default values

        Returns:
            List[Any]: List of created instances
        """
        return [cls.create(**kwargs) for _ in range(size)]


class DictFactory(BaseFactory):
    """
    Factory for creating dictionary-based test data.

    This class provides functionality for generating dictionaries
    with random data, useful for API response mocking.
    """

    # Default dictionary fields and their generation functions
    DEFAULTS: Dict[str, callable] = {}

    @classmethod
    def create(cls, **kwargs: Any) -> Dict[str, Any]:
        """
        Create a dictionary with random test data.

        Args:
            **kwargs: Fields to override default values

        Returns:
            Dict[str, Any]: Dictionary with test data
        """
        # Start with default values
        data = {}

        # Apply defaults for fields not in kwargs
        for field, default_func in cls.DEFAULTS.items():
            if field not in kwargs:
                data[field] = default_func()

        # Override with provided values
        data.update(kwargs)

        return data


class ModelFactory(BaseFactory):
    """
    Factory for creating model-based test data.

    This class provides functionality for generating instances
    of data models (e.g., Pydantic models) with random data.
    """

    # Model class to create instances of
    MODEL_CLASS: Optional[Type[Any]] = None

    # Default model fields and their generation functions
    DEFAULTS: Dict[str, callable] = {}

    @classmethod
    def create(cls, **kwargs: Any) -> Any:
        """
        Create a model instance with random test data.

        Args:
            **kwargs: Fields to override default values

        Returns:
            Any: Model instance with test data
        """
        if cls.MODEL_CLASS is None:
            raise ValueError(f"MODEL_CLASS not defined for {cls.__name__}")

        # Start with default values
        data = {}

        # Apply defaults for fields not in kwargs
        for field, default_func in cls.DEFAULTS.items():
            if field not in kwargs:
                data[field] = default_func()

        # Override with provided values
        data.update(kwargs)

        # Create and return model instance
        return cls.MODEL_CLASS(**data)


class SQLAlchemyModelFactory(ModelFactory):
    """
    Factory for creating SQLAlchemy model instances for testing.

    This class extends ModelFactory with functionality specific to
    SQLAlchemy models, including session handling and persistence.
    """

    @classmethod
    def create_and_persist(cls, session: Any, **kwargs: Any) -> Any:
        """
        Create a model instance and persist it to the database.

        Args:
            session: SQLAlchemy session to use for persistence
            **kwargs: Fields to override default values

        Returns:
            Any: Created and persisted model instance
        """
        instance = cls.create(**kwargs)
        session.add(instance)
        session.flush()  # Flush to get generated IDs
        return instance

    @classmethod
    def create_batch_and_persist(cls, session: Any, size: int, **kwargs: Any) -> List[Any]:
        """
        Create multiple model instances and persist them to the database.

        Args:
            session: SQLAlchemy session to use for persistence
            size: Number of instances to create
            **kwargs: Fields to override default values

        Returns:
            List[Any]: List of created and persisted model instances
        """
        instances = cls.create_batch(size, **kwargs)
        for instance in instances:
            session.add(instance)
        session.flush()  # Flush to get generated IDs
        return instances
