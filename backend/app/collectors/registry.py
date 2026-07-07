from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Optional, Type

from app.collectors.base import BaseCollector


class CollectorRegistry:
    """Auto-discovery registry for job collectors.

    Collectors register themselves via inheritance from BaseCollector.
    The registry discovers them by scanning specified packages.

    No collector is hardcoded. Adding a new collector requires only:
    1. Create a class that inherits from BaseCollector
    2. Place it in a registered plugin package
    """

    _collectors: dict[str, type[BaseCollector]] = {}

    @classmethod
    def register(cls, collector_class: type[BaseCollector]) -> type[BaseCollector]:
        """Register a collector class manually.

        Called automatically when the class is imported if it
        inherits from BaseCollector and the module is scanned.

        Args:
            collector_class: A class inheriting from BaseCollector.

        Returns:
            The same class (for decorator use).

        Raises:
            TypeError: If the class does not inherit from BaseCollector.
        """
        if not (
            inspect.isclass(collector_class)
            and issubclass(collector_class, BaseCollector)
            and collector_class is not BaseCollector
        ):
            raise TypeError(
                f"{collector_class.__name__} must inherit from BaseCollector"
            )

        instance = collector_class.__new__(collector_class)
        name = instance.name
        if name in cls._collectors:
            raise ValueError(
                f"Collector '{name}' is already registered. "
                f"Existing: {cls._collectors[name].__name__}, "
                f"New: {collector_class.__name__}"
            )
        cls._collectors[name] = collector_class
        return collector_class

    @classmethod
    def discover(cls, *packages: str) -> dict[str, type[BaseCollector]]:
        """Scan packages for BaseCollector subclasses and register them.

        Args:
            *packages: Fully qualified package names to scan
                       (e.g., 'app.collectors.plugins').

        Returns:
            Dictionary of {collector_name: collector_class}.
        """
        for package in packages:
            try:
                pkg = importlib.import_module(package)
            except ImportError:
                continue

            path = getattr(pkg, "__path__", [])
            for _, module_name, _ in pkgutil.iter_modules(path):
                full_module = f"{package}.{module_name}"
                try:
                    module = importlib.import_module(full_module)
                except ImportError:
                    continue

                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseCollector)
                        and obj is not BaseCollector
                        and obj.__module__ == full_module
                    ):
                        try:
                            cls.register(obj)
                        except (TypeError, ValueError):
                            continue

        return cls._collectors

    @classmethod
    def get(cls, name: str) -> Optional[type[BaseCollector]]:
        """Get a registered collector class by name.

        Args:
            name: Collector name (e.g., 'linkedin', 'greenhouse').

        Returns:
            The collector class, or None if not found.
        """
        return cls._collectors.get(name)

    @classmethod
    def list_collectors(cls) -> list[str]:
        """List all registered collector names.

        Returns:
            Sorted list of collector names.
        """
        return sorted(cls._collectors.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered collectors (useful for testing)."""
        cls._collectors.clear()
