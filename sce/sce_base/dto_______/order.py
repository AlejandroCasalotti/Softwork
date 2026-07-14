# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass, field

from .base import BaseDTO


@dataclass(frozen=True, slots=True)
class OrderDTO(BaseDTO):
    external_id: str

    status: str

    buyer_name: str

    currency: str

    total: float

    created_at: str | None = None

    lines: tuple = field(default_factory=tuple)