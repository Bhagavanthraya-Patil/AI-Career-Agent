from __future__ import annotations

import inspect
from typing import Any, Optional, Type

from app.extractors.base import BaseExtractor


class ExtractorRegistry:
    """Registry for extractor discovery and registration.

    Follows the same pattern as ``ParserRegistry`` and ``CollectorRegistry``.
    Extractors register themselves, and the registry enables lookup by name.

    Adding a new extractor requires only:
    1. Create a class inheriting from ``BaseExtractor``
    2. Set the ``name`` class attribute
    3. Call ``ExtractorRegistry.register()`` or import the module
    """

    _extractors: dict[str, type[BaseExtractor]] = {}
    _instances: dict[str, BaseExtractor] = {}

    @classmethod
    def register(
        cls,
        extractor_class: type[BaseExtractor],
    ) -> type[BaseExtractor]:
        """Register an extractor class.

        Args:
            extractor_class: A class inheriting from BaseExtractor.

        Returns:
            The same class (for decorator use).

        Raises:
            TypeError: If the class does not inherit from BaseExtractor.
            ValueError: If the extractor name is already registered.
        """
        if not (
            inspect.isclass(extractor_class)
            and issubclass(extractor_class, BaseExtractor)
            and extractor_class is not BaseExtractor
        ):
            raise TypeError(
                f"{extractor_class.__name__} must inherit from BaseExtractor"
            )

        name = extractor_class.name
        if name in cls._extractors:
            raise ValueError(
                f"Extractor '{name}' is already registered. "
                f"Existing: {cls._extractors[name].__name__}, "
                f"New: {extractor_class.__name__}"
            )
        cls._extractors[name] = extractor_class
        return extractor_class

    @classmethod
    def get(
        cls,
        name: str,
        config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[BaseExtractor]:
        """Get an extractor instance by name.

        Args:
            name: Extractor name (e.g., 'salary', 'location').
            config: Optional configuration override.
            **kwargs: Additional constructor arguments.

        Returns:
            An instantiated extractor, or None if not found.
        """
        extractor_class = cls._extractors.get(name)
        if extractor_class is None:
            return None
        return extractor_class(config=config, **kwargs)

    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[BaseExtractor]:
        """Get a cached extractor instance, creating it if needed.

        Args:
            name: Extractor name.
            config: Optional configuration override.
            **kwargs: Additional constructor arguments.

        Returns:
            An extractor instance (possibly cached).
        """
        if name in cls._instances:
            return cls._instances[name]
        instance = cls.get(name, config=config, **kwargs)
        if instance is not None:
            cls._instances[name] = instance
        return instance

    @classmethod
    def list_extractors(cls) -> list[str]:
        """List all registered extractor names.

        Returns:
            Sorted list of extractor names.
        """
        return sorted(cls._extractors.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered extractors (useful for testing)."""
        cls._extractors.clear()
        cls._instances.clear()
