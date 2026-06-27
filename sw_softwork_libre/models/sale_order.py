# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ml_order_id = fields.Char(string="ML Order ID", index=True, copy=False)
    ml_account_id = fields.Many2one("sw.ml.account", string="Cuenta ML", copy=False)

    def action_ml_import_orders(self, account=None, integration=None):
        if not account:
            account = self.env["sw.ml.account"].search([("active", "=", True)], limit=1)
        if not account or not account.seller_id:
            return {"created": 0, "skipped": 0, "errors": 0}

        try:
            data = account._ml_request(
                "GET",
                "/orders/search",
                params={"seller": account.seller_id, "sort": "date_desc"},
            )
        except Exception as err:
            _logger.exception("Error obteniendo órdenes de MercadoLibre: %s", err)
            return {"created": 0, "skipped": 0, "errors": 1}

        stats = {"created": 0, "skipped": 0, "errors": 0}
        results = (data or {}).get("results", [])
        for order_data in results:
            try:
                ml_order_id = str(order_data.get("id") or "")
                if not ml_order_id:
                    stats["skipped"] += 1
                    continue
                existing = self.search([("ml_order_id", "=", ml_order_id)], limit=1)
                if existing:
                    stats["skipped"] += 1
                    continue

                partner = self.env.ref("base.public_partner")
                sale = self.create({
                    "partner_id": partner.id,
                    "ml_order_id": ml_order_id,
                    "ml_account_id": account.id,
                    "origin": f"MercadoLibre {ml_order_id}",
                })

                for item in order_data.get("order_items", []):
                    i = item.get("item") or {}
                    qty = float(item.get("quantity") or 0.0)
                    unit_price = float(item.get("unit_price") or 0.0)
                    title = i.get("title") or "Producto MercadoLibre"
                    ml_item_id = i.get("id")

                    product = self.env["product.product"].search(
                        [("product_tmpl_id.ml_item_id", "=", ml_item_id)],
                        limit=1,
                    )
                    if not product:
                        product = self.env["product.product"].search([], limit=1)

                    self.env["sale.order.line"].create({
                        "order_id": sale.id,
                        "product_id": product.id if product else False,
                        "name": title,
                        "product_uom_qty": qty if qty > 0 else 1.0,
                        "price_unit": unit_price,
                    })
                stats["created"] += 1
            except Exception as err:
                stats["errors"] += 1
                _logger.exception("Error creando orden ML %s: %s", order_data, err)

        if integration:
            _logger.info("Integración %s import orders stats: %s", integration.display_name, stats)
        return stats

    @classmethod
    def cron_ml_import_orders(cls, env):
        integrations = env["sw.integration"].search([
            ("state", "=", "confirmed"),
            ("integration_type_id", "=", "meli"),
            ("sync_orders", "=", True),
        ])
        for integration in integrations:
            env["sale.order"].action_ml_import_orders(
                account=integration.meli_account_id,
                integration=integration,
            )