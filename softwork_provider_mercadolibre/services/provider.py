# -*- coding: utf-8 -*-
"""
Factory externa para proveedor MercadoLibre desacoplado.
Convención esperada por softwork_ecommerce_conector_base ProviderFactory:
softwork_provider_mercadolibre.services.provider.get_provider
"""

from odoo.exceptions import UserError

from softwork_ecommerce_conector_base.services.providers.ml_provider import MercadoLibreProvider


def get_provider(env, account):
    provider_type = (account.connector_id.provider_type or "").strip().lower()
    if provider_type != "mercadolibre":
        raise UserError(f"Invalid provider_type for softwork_provider_mercadolibre: {provider_type}")
    return MercadoLibreProvider(env, account)
