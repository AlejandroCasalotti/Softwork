# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

HTTP Response
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HttpResponse:
    """
    Normalized HTTP response returned by :class:`HttpClient`.
    """

    status_code: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status_code < 400
