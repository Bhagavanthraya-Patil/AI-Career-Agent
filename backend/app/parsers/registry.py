from __future__ import annotations

import inspect
from typing import Any, Optional, Type

from app.parsers.base import BaseParser


class ParserRegistry:
    """Registry for parser discovery and registration.

    Follows the same pattern as ``CollectorRegistry``. Parsers
    register themselves, and the registry enables lookup by name.

    Adding a new parser requires only:
    1. Create a class inheriting from ``BaseParser``
    2. Set the ``name`` class attribute
    3. Call ``ParserRegistry.register()`` or import the module
    """

    _parsers: dict[str, type[BaseParser]] = {}
    _instances: dict[str, BaseParser] = {}

    @classmethod
    def register(
        cls,
        parser_class: type[BaseParser],
    ) -> type[BaseParser]:
        """Register a parser class.

        Args:
            parser_class: A class inheriting from BaseParser.

        Returns:
            The same class (for decorator use).

        Raises:
            TypeError: If the class does not inherit from BaseParser.
            ValueError: If the parser name is already registered.
        """
        if not (
            inspect.isclass(parser_class)
            and issubclass(parser_class, BaseParser)
            and parser_class is not BaseParser
        ):
            raise TypeError(
                f"{parser_class.__name__} must inherit from BaseParser"
            )

        name = parser_class.name
        if name in cls._parsers:
            raise ValueError(
                f"Parser '{name}' is already registered. "
                f"Existing: {cls._parsers[name].__name__}, "
                f"New: {parser_class.__name__}"
            )
        cls._parsers[name] = parser_class
        return parser_class

    @classmethod
    def get(
        cls,
        name: str,
        config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[BaseParser]:
        """Get a parser instance by name.

        Args:
            name: Parser name (e.g., 'salary', 'location').
            config: Optional configuration override.
            **kwargs: Additional constructor arguments.

        Returns:
            An instantiated parser, or None if not found.
        """
        parser_class = cls._parsers.get(name)
        if parser_class is None:
            return None
        return parser_class(config=config, **kwargs)

    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[BaseParser]:
        """Get a cached parser instance, creating it if needed.

        Args:
            name: Parser name.
            config: Optional configuration override.
            **kwargs: Additional constructor arguments.

        Returns:
            A parser instance (possibly cached).
        """
        if name in cls._instances:
            return cls._instances[name]
        instance = cls.get(name, config=config, **kwargs)
        if instance is not None:
            cls._instances[name] = instance
        return instance

    @classmethod
    def list_parsers(cls) -> list[str]:
        """List all registered parser names.

        Returns:
            Sorted list of parser names.
        """
        return sorted(cls._parsers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered parsers (useful for testing)."""
        cls._parsers.clear()
        cls._instances.clear()
