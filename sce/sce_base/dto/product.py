# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass, field

from .base import BaseDTO


@dataclass(frozen=True, slots=True)
class ProductDTO(BaseDTO):
    external_id: str | None = None
    sku: str | None = None
    barcode: str | None = None

    name: str = ""

    description: str = ""

    price: float = 0.0

    currency: str = "ARS"

    stock: float = 0.0

    images: tuple[str, ...] = field(default_factory=tuple)

    attributes: dict[str, str] = field(default_factory=dict)