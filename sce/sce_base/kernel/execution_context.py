# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ExecutionContext:
    """
    Runtime execution context.

    It carries all runtime information required by Providers without
    exposing Odoo internals directly.
    """

    env: Any
    account: Any = None
    company: Any = None
    user: Any = None
    logger: Any = None
    metadata: dict | None = None

    def get(self, key: str, default=None):
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def set(self, key: str, value):
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value