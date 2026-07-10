# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseDTO


@dataclass(frozen=True, slots=True)
class StockDTO(BaseDTO):
    sku: str

    quantity: float