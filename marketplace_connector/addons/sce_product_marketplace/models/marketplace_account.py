# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceAccount(models.Model):
    _inherit = "sce.account"

    marketplace_auto_confirm_paid = fields.Boolean(
        string="Confirmar órdenes pagadas automáticamente", default=False
    )
    marketplace_auto_cancelled = fields.Boolean(
        string="Cancelar órdenes canceladas automáticamente", default=False
    )