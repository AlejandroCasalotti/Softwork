# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Base Plugin
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .base_provider import BaseProvider
from .plugin_descriptor import PluginDescriptor


class BasePlugin(ABC):
    """
    Base class for all marketplace plugins.

    A plugin exposes metadata and provides the Provider used by
    the SCE Kernel.

    Plugins MUST NOT contain business logic.
    """

    @property
    @abstractmethod
    def descriptor(self) -> PluginDescriptor:
        """
        Returns plugin metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def get_provider(self) -> BaseProvider:
        """
        Returns the Provider associated with this plugin.
        """
        raise NotImplementedError

    @property
    def code(self) -> str:
        return self.descriptor.code

    @property
    def name(self) -> str:
        return self.descriptor.name

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"code='{self.code}'>"
        )