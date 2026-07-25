# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


class OdooProvider:
    """
    Provider externo base para conectores tipo 'odoo'.
    Implementación mínima para cumplir contrato de carga dinámica.
    """

    def __init__(self, env, account):
        self.env = env
        self.account = account

    def ping(self):
        return {
            "ok": True,
            "provider": "odoo",
            "account_id": self.account.id,
            "connector_id": self.account.connector_id.id,
        }


def get_provider(env, account):
    """
    Factory requerida por convención:
    <modulo>.services.provider.get_provider
    """
    _logger.info(
        "Resolviendo provider externo Odoo para cuenta %s (connector %s)",
        account.id,
        account.connector_id.id,
    )
    return OdooProvider(env, account)