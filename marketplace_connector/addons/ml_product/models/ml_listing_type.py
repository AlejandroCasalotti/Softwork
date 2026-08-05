# -*- coding: utf-8 -*-
from odoo import fields, models


class MlListingType(models.Model):
    _name = "ml.listing.type"
    _description = "Tipos de publicación ML"
    _order = "name"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    listing_type_id = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    status = fields.Char()

    _ml_listing_type_unique = models.Constraint(
        "unique(account_id, listing_type_id)",
        "El tipo de publicación ya existe para esta cuenta.",
    )