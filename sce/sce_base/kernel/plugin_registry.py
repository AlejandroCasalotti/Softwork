# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Plugin Registry

Stores all registered marketplace plugins available at runtime.
"""

from __future__ import annotations

from threading import RLock
from typing import Dict, Iterable

from .plugin_descriptor import PluginDescriptor


class PluginRegistry:
    """
    Thread-safe registry of marketplace plugins.

    The registry stores PluginDescriptor objects only.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginDescriptor] = {}
        self._lock = RLock()

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self, descriptor: PluginDescriptor) -> None:
        """
        Register a new marketplace plugin.

        :param descriptor: PluginDescriptor
        """

        if not isinstance(descriptor, PluginDescriptor):
            raise TypeError(
                "descriptor must be an instance of PluginDescriptor."
            )

        code = descriptor.code.strip().lower()

        with self._lock:

            if code in self._plugins:
                raise ValueError(
                    f"Plugin '{code}' is already registered."
                )

            self._plugins[code] = descriptor

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get(self, code: str) -> PluginDescriptor | None:
        """
        Return a PluginDescriptor.

        :param code: Connector code.
        """

        if not code:
            return None

        return self._plugins.get(code.strip().lower())

    def exists(self, code: str) -> bool:
        """
        Check whether a plugin exists.
        """

        return self.get(code) is not None

    # -------------------------------------------------------------------------
    # Iteration
    # -------------------------------------------------------------------------

    def all(self) -> Iterable[PluginDescriptor]:
        """
        Return all registered plugins.
        """

        return tuple(self._plugins.values())

    def codes(self) -> tuple[str, ...]:
        """
        Return registered connector codes.
        """

        return tuple(sorted(self._plugins.keys()))

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def count(self) -> int:
        """
        Number of registered plugins.
        """

        return len(self._plugins)

    def clear(self) -> None:
        """
        Clear registry.

        Mainly used during tests.
        """

        with self._lock:
            self._plugins.clear()

    # -------------------------------------------------------------------------
    # Python API
    # -------------------------------------------------------------------------

    def __contains__(self, code: str) -> bool:
        return self.exists(code)

    def __iter__(self):
        return iter(self.all())

    def __len__(self):
        return self.count()

    def __repr__(self):
        return (
            f"<PluginRegistry plugins={self.count()}>"
        )