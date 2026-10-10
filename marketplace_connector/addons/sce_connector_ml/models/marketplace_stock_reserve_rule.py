# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceStockReserveRule(models.Model):
    _name = "marketplace.stock.reserve.rule"
    _description = "Reserva de stock por SKU para marketplace"
    _order = "sku"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    sku = fields.Char(string="SKU / Referencia interna", required=True, index=True)
    reserve_qty = fields.Integer(string="Cantidad a reservar", default=0, required=True)
    active = fields.Boolean(default=True)
    note = fields.Char(string="Nota")

    _stock_reserve_unique = models.Constraint(
        "UNIQUE(account_id, sku)",
        "Ya existe una regla de reserva para este SKU en esta cuenta.",
    )
