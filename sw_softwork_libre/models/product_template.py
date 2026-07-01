# -*- coding: utf-8 -*-
import logging

from odoo import fields, models
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_sync_enabled = fields.Boolean(string="Sincronizar con MercadoLibre", default=False)
    ml_item_id = fields.Char(string="ML Item ID")
    ml_listing_type = fields.Char(string="ML Listing Type")
    ml_last_sync = fields.Datetime(string="Última sincronización ML")

    def _get_qty_for_integration(self, integration):
        self.ensure_one()
        if integration and integration.stock_location_ids:
            locations = self.env["stock.location"].search([("id", "child_of", integration.stock_location_ids.ids)])
            quants = self.env["stock.quant"].read_group(
                [
                    ("product_id", "in", self.product_variant_ids.ids),
                    ("location_id", "in", locations.ids),
                ],
                ["quantity:sum"],
                [],
            )
            qty = quants[0]["quantity"] if quants else 0.0
            return qty or 0.0
        if integration and integration.odoo_stock_location_id:
            location = integration.odoo_stock_location_id
            locations = self.env["stock.location"].search([("id", "child_of", location.id)])
            quants = self.env["stock.quant"].read_group(
                [
                    ("product_id", "in", self.product_variant_ids.ids),
                    ("location_id", "in", locations.ids),
                ],
                ["quantity:sum"],
                [],
            )
            qty = quants[0]["quantity"] if quants else 0.0
            return qty or 0.0
        return sum(self.product_variant_ids.mapped("qty_available"))

    def _get_price_for_integration(self, integration):
        self.ensure_one()
        pricelist = integration.odoo_default_pricelist_id if integration else False
        if not pricelist:
            base_price = self.list_price
        else:
            product = self.product_variant_id or self.product_variant_ids[:1]
            base_price = pricelist._get_product_price(product, 1.0) if product else self.list_price

        if integration and self.ml_listing_type == "gold_pro" and integration.meli_odoo_premium_pricelist_id:
            product = self.product_variant_id or self.product_variant_ids[:1]
            if product:
                base_price = integration.meli_odoo_premium_pricelist_id._get_product_price(product, 1.0)

        final_price = base_price or 0.0

        if integration and integration.meli_advanced_prices:
            for line in integration.meli_installment_ids:
                if line.surcharge_percent:
                    final_price = max(final_price, base_price * (1.0 + (line.surcharge_percent / 100.0)))

        if integration and integration.meli_surcharge_minimum and final_price >= integration.meli_surcharge_minimum:
            if integration.meli_percentage_surcharge:
                final_price += final_price * (integration.meli_percentage_surcharge / 100.0)
            if integration.meli_fixed_surcharge:
                final_price += integration.meli_fixed_surcharge

        return float_round(final_price, precision_digits=2)

    def action_ml_sync_price_stock(self, account=None, integration=None, mode="both"):
        if not account:
            account = self.env["sw.ml.account"].search([("active", "=", True)], limit=1)
        if not account:
            return {"ok": 0, "error": 0, "skipped": len(self)}

        stats = {"ok": 0, "error": 0, "skipped": 0}
        for template in self:
            if not template.ml_sync_enabled or not template.ml_item_id:
                stats["skipped"] += 1
                continue

            payload = {}
            if mode in ("both", "price"):
                payload["price"] = template._get_price_for_integration(integration)
            if mode in ("both", "stock"):
                qty = template._get_qty_for_integration(integration)
                payload["available_quantity"] = int(qty)

            if not payload:
                stats["skipped"] += 1
                continue

            try:
                account._ml_request("PUT", f"/items/{template.ml_item_id}", payload=payload)
                template.ml_last_sync = fields.Datetime.now()
                stats["ok"] += 1
            except Exception as err:
                stats["error"] += 1
                _logger.exception("Error sincronizando producto %s: %s", template.display_name, err)
        return stats

    @classmethod
    def cron_ml_sync_products(cls, env):
        integrations = env["sw.integration"].search([
            ("state", "=", "confirmed"),
            ("integration_type_id", "=", "meli"),
        ])
        for integration in integrations:
            products = env["product.template"].search([
                ("ml_sync_enabled", "=", True),
                ("ml_item_id", "!=", False),
            ])
            if integration.sync_prices:
                products.action_ml_sync_price_stock(
                    account=integration.meli_account_id,
                    integration=integration,
                    mode="price",
                )
            if integration.sync_stock:
                products.action_ml_sync_price_stock(
                    account=integration.meli_account_id,
                    integration=integration,
                    mode="stock",
                )