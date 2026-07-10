# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Mercado Libre Plugin Descriptor.
"""

from __future__ import annotations

from odoo import _

from ...sce_base.kernel.plugin import Plugin
from ..providers.mercadolibre_provider import MercadoLibreProvider


class MercadoLibrePlugin(Plugin):
    """
    Mercado Libre plugin definition.
    """

    code = "mercadolibre"

    name = _("Mercado Libre")

    version = "1.0.0"

    provider_class = MercadoLibreProvider

    description = _(
        "Official Mercado Libre connector for "
        "Softwork Commerce Engine."
    )

    author = "Softwork"

    website = "https://swsistemas.com"

    supported_features = {
        "oauth",
        "products",
        "stock",
        "price",
        "orders",
        "shipments",
        "questions",
        "messages",
        "webhooks",
    }