# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Type


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """
    Immutable description of a marketplace plugin.

    This class contains only the information required by the
    Kernel to identify and instantiate a plugin.
    """

    #: Unique connector code (ml, shopify, amazon, ...)
    code: str

    #: Human readable name
    name: str

    #: Plugin implementation class
    plugin_class: Type

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", self.code.strip().lower())

        if not self.code:
            raise ValueError("Plugin code cannot be empty.")

        if not self.name:
            raise ValueError("Plugin name cannot be empty.")

        if self.plugin_class is None:
            raise ValueError("Plugin class is required.")