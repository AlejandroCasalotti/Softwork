# -*- coding: utf-8 -*-
from odoo import fields, models


class SceConnector(models.Model):
    _name = "sce.connector"
    _description = "SCE Connector"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    provider_type = fields.Selection(
        selection=[
            ("mercadolibre", "MercadoLibre"),
            ("shopify", "Shopify"),
            ("amazon", "Amazon"),
            ("tiendanube", "Tiendanube"),
            ("woocommerce", "WooCommerce"),
            ("custom", "Custom"),
        ],
        required=True,
        default="custom",
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    account_ids = fields.One2many("sce.account", "connector_id", string="Accounts")
    description = fields.Text()
    provider_impl_path = fields.Char(
        string="Provider Implementation Path",
        help=(
            "Optional dotted path for external provider factory. "
            "Example: softwork_provider_mercadolibre.services.provider.get_provider"
        ),
        tracking=True,
    )