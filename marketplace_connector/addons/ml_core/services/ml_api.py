# -*- coding: utf-8 -*-
from odoo.exceptions import UserError


class MercadoLibreAPIService:
    """
    Servicio liviano para centralizar llamadas API.
    """

    def __init__(self, account):
        self.account = account

    def request(self, method, endpoint, payload=None, params=None):
        if not self.account:
            raise UserError("No hay cuenta MercadoLibre configurada.")
        return self.account.ml_request(method, endpoint, payload=payload, params=params)