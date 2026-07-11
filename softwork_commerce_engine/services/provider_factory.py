# -*- coding: utf-8 -*-
from odoo.exceptions import UserError

from .providers.ml_provider import MercadoLibreProvider


class ProviderFactory:
    """
    Factory para resolver providers por tipo de conector.
    """

    @staticmethod
    def get_provider(account):
        provider_type = (account.connector_id.provider_type or "").strip().lower()
        if provider_type == "mercadolibre":
            return MercadoLibreProvider(account.env, account)
        raise UserError(f"Provider not implemented yet for type: {provider_type}")