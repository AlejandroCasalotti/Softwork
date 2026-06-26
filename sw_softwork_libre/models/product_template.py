# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_sync_enabled = fields.Boolean(string="Sincronizar con MercadoLibre", default=False)
    ml_item_id = fields.Char(string="ML Item ID")
    ml_listing_type = fields.Char(string="ML Listing Type")
    ml_last_sync = fields.Datetime(string="Última sincronización ML")

    def action_ml_sync_price_stock(self):
        account = self.env["sw.ml.account"].search([("active", "=", True)], limit=1)
        if not account:
            return

        for template in self:
            if not template.ml_sync_enabled or not template.ml_item_id:
                continue
            qty = sum(template.product_variant_ids.mapped("qty_available"))
            payload = {
                "price": template.list_price,
                "available_quantity": int(qty),
            }
            try:
                account._ml_request("PUT", f"/items/{template.ml_item_id}", payload=payload)
                template.ml_last_sync = fields.Datetime.now()
            except Exception as err:
                _logger.exception("Error sincronizando producto %s: %s", template.display_name, err)

    @classmethod
    def cron_ml_sync_products(cls, env):
        products = env["product.template"].search([
            ("ml_sync_enabled", "=", True),
            ("ml_item_id", "!=", False),
        ])
        products.action_ml_sync_price_stock()