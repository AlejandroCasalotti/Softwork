# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Base Provider Contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import FrozenSet


class BaseProvider(ABC):
    """
    Base class for every marketplace provider.

    Providers contain all marketplace-specific business logic.

    They must remain independent from Odoo models.
    """

    @property
    @abstractmethod
    def code(self) -> str:
        """
        Unique provider code.

        Example:
            ml
            shopify
            amazon
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable provider name.
        """
        raise NotImplementedError

    @property
    def capabilities(self) -> FrozenSet[str]:
        """
        Supported provider capabilities.

        Override in subclasses.
        """
        return frozenset()

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def supports(self, capability: str) -> bool:
        """
        Return True if the provider supports a capability.
        """
        return capability in self.capabilities

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def connect(self, context):
        """
        Start authentication flow.
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, context):
        """
        Disconnect account.
        """
        raise NotImplementedError

    @abstractmethod
    def test_connection(self, context):
        """
        Validate credentials.
        """
        raise NotImplementedError