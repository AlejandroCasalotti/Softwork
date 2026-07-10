# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class BaseDTO:
    """
    Base class for all DTOs used by SCE.

    DTOs are immutable transport objects.
    They must not contain business logic or references to Odoo models.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Return the DTO as a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, values: Dict[str, Any]):
        """Create a DTO instance from a dictionary."""
        return cls(**values)