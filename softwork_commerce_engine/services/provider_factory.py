# -*- coding: utf-8 -*-
from odoo.exceptions import UserError


class ProviderFactory:
    """
    Factory base para resolver providers por tipo de conector.
    En fases siguientes se mapearán implementaciones concretas.
    """

    @staticmethod
    def get_provider(account):
        provider_type = account.connector_id.provider_type
        raise UserError(f"Provider not implemented yet for type: {provider_type}")