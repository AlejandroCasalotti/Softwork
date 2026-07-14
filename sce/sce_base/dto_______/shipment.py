# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseDTO


@dataclass(frozen=True, slots=True)
class ShipmentDTO(BaseDTO):
    external_id: str

    status: str

    tracking_number: str | None = None

    carrier: str | None = None