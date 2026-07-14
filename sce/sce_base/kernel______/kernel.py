# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Kernel
"""

from __future__ import annotations

from .plugin_registry import PluginRegistry


class Kernel:
    """
    Central entry point for resolving marketplace plugins
    and providers.
    """

    def __init__(self, registry: PluginRegistry):
        self._registry = registry

    @property
    def registry(self) -> PluginRegistry:
        """
        Returns the plugin registry.
        """
        return self._registry

    # ---------------------------------------------------------
    # Registration
    # ---------------------------------------------------------

    def register(self, descriptor):
        """
        Register a plugin descriptor.
        """
        self._registry.register(descriptor)

    # ---------------------------------------------------------
    # Plugin Resolution
    # ---------------------------------------------------------

    def get_plugin(self, code: str):
        """
        Returns a plugin instance.
        """

        descriptor = self._registry.get(code)

        if descriptor is None:
            raise ValueError(
                f"Unknown connector '{code}'."
            )

        return descriptor.plugin_class()

    def get_provider(self, code: str):
        """
        Returns the Provider associated with a connector.
        """

        plugin = self.get_plugin(code)

        return plugin.get_provider()

    # ---------------------------------------------------------
    # Registry helpers
    # ---------------------------------------------------------

    def installed_plugins(self):
        """
        Returns all installed plugin descriptors.
        """

        return self.registry.all()

    def has_plugin(self, code: str) -> bool:
        """
        Returns True if connector exists.
        """

        return self.registry.exists(code)

    def plugin_count(self) -> int:
        """
        Number of installed plugins.
        """

        return self.registry.count()

    def __repr__(self):
        return (
            f"<Kernel plugins={self.plugin_count()}>"
        )