# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

HTTP Authentication Strategies
"""

from __future__ import annotations

import abc


class AuthStrategy(abc.ABC):
    """
    Base class for outbound HTTP authentication strategies.
    """

    @abc.abstractmethod
    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Returns a new headers dict augmented with authentication data.
        """


class BearerAuth(AuthStrategy):
    """
    Authenticates requests with an ``Authorization: Bearer <token>`` header.
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        result = dict(headers or {})
        result["Authorization"] = f"Bearer {self.token}"
        return result
