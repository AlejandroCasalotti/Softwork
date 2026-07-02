# -*- coding: utf-8 -*-
import json
import logging
import math

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_sync_enabled = fields.Boolean(string="Sincronizar con MercadoLibre", default=False)
    ml_sync_active = fields.Boolean(string="Publicación activa", default=True)
    ml_item_id = fields.Char(string="ML Item ID")
    ml_listing_type = fields.Char(string="ML Listing Type")
    ml_last_sync = fields.Datetime(string="Última sincronización ML")

    ml_sku = fields.Char(string="SKU ML")
    ml_listing_description = fields.Text(string="Descripción de la publicación")
    ml_reserved_stock_percent = fields.Float(string="Stock reservado %", default=100.0)
    ml_sale_price = fields.Float(string="Precio de venta ML")
    ml_markup_percent = fields.Float(string="Aumento por porcentaje")
    ml_extra_fee = fields.Float(string="Tarifa extra")
    ml_fee_option_id = fields.Char(string="Opción cargo por vender/cuotas")
    ml_fee_option_json = fields.Text(string="Detalle opción de cargos")
    ml_fee_markup_percent = fields.Float(string="Aumento sobre opción de cargo (%)")
    ml_shipping_mode = fields.Char(string="Forma de entrega")
    ml_warranty_type = fields.Char(string="Garantía")
    ml_publish_state = fields.Selection(
        [("draft", "Borrador"), ("published", "Publicado"), ("deleted", "Eliminado")],
        default="draft",
        string="Estado publicación ML",
    )
    ml_net_price = fields.Float(string="Precio neto publicación", compute="_compute_ml_net_price", store=False)
    ml_effective_sku = fields.Char(string="SKU efectivo", compute="_compute_ml_effective_values", store=False)
    ml_effective_description = fields.Text(string="Descripción efectiva", compute="_compute_ml_effective_values", store=False)
    ml_effective_sale_price = fields.Float(string="Precio efectivo", compute="_compute_ml_effective_values", store=False)
    ml_publish_qty = fields.Integer(string="Stock publicación", compute="_compute_ml_publish_qty", store=False)

    ml_photo_ids = fields.One2many("sw.product.ml.photo", "product_tmpl_id", string="Fotos publicación")

    @api.depends("ml_sku", "default_code", "ml_listing_description", "name", "ml_sale_price", "list_price")
    def _compute_ml_effective_values(self):
        for rec in self:
            rec.ml_effective_sku = rec.ml_sku or rec.default_code or ""
            rec.ml_effective_description = rec.ml_listing_description or rec.name or ""
            rec.ml_effective_sale_price = rec.ml_sale_price if rec.ml_sale_price > 0 else rec.list_price

    @api.depends("ml_effective_sale_price", "ml_markup_percent", "ml_extra_fee", "ml_fee_markup_percent")
    def _compute_ml_net_price(self):
        for rec in self:
            price = rec.ml_effective_sale_price or 0.0
            if rec.ml_markup_percent:
                price += price * (rec.ml_markup_percent / 100.0)
            if rec.ml_extra_fee:
                price += rec.ml_extra_fee
            if rec.ml_fee_markup_percent:
                price += price * (rec.ml_fee_markup_percent / 100.0)
            rec.ml_net_price = float_round(price, precision_digits=2)

    @api.depends("ml_reserved_stock_percent", "product_variant_ids.free_qty")
    def _compute_ml_publish_qty(self):
        for rec in self:
            available = sum(rec.product_variant_ids.mapped("free_qty"))
            if available <= 0:
                rec.ml_publish_qty = 0
                continue
            percent = rec.ml_reserved_stock_percent if rec.ml_reserved_stock_percent >= 0 else 0.0
            qty = available * (percent / 100.0)
            rec.ml_publish_qty = int(math.ceil(qty)) if qty > 0 else 0

    def _get_ml_account(self):
        account = self.env["sw.ml.account"].search([("active", "=", True), ("access_token", "!=", False)], limit=1)
        if not account:
            raise UserError("No hay una cuenta MercadoLibre activa y autenticada.")
        return account

    def _prepare_ml_payload(self):
        self.ensure_one()
        title = (self.ml_listing_description or self.name or "").strip()
        if not title:
            raise UserError("Debes completar Nombre del producto o Descripción de publicación.")
        sku = (self.ml_sku or self.default_code or "").strip()
        if not sku:
            raise UserError("Debes completar SKU o Referencia interna (default_code).")

        pictures = []
        for photo in self.ml_photo_ids.sorted("sequence"):
            if photo.image_1920:
                pictures.append({"source": f"data:image/png;base64,{photo.image_1920.decode() if isinstance(photo.image_1920, bytes) else photo.image_1920}"})

        payload = {
            "title": title[:60],
            "category_id": "MLA3530",
            "price": self.ml_net_price or self.list_price,
            "currency_id": "ARS",
            "available_quantity": max(0, self.ml_publish_qty),
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": self.ml_listing_type or "gold_special",
            "description": {"plain_text": self.ml_effective_description or self.name},
            "attributes": [{"id": "SELLER_SKU", "value_name": sku}],
            "shipping": {"mode": self.ml_shipping_mode or "me2"},
            "warranty": self.ml_warranty_type or "Garantía del vendedor",
        }
        if pictures:
            payload["pictures"] = pictures
        return payload

    def action_ml_search_catalog(self):
        self.ensure_one()
        account = self._get_ml_account()
        query = (self.ml_listing_description or self.name or "").strip()
        if not query:
            raise UserError("Primero completa la Descripción de la publicación o el Nombre del producto.")
        result = account._ml_request("GET", "/sites/MLA/domain_discovery/search", params={"q": query})
        self.ml_fee_option_json = json.dumps(result, ensure_ascii=False, indent=2)
        return True

    def action_ml_select_fee_option(self):
        self.ensure_one()
        account = self._get_ml_account()
        if not self.ml_listing_type:
            raise UserError("Completa ML Listing Type para consultar cargos.")
        listing = account._ml_request("GET", f"/sites/MLA/listing_prices", params={"price": self.ml_effective_sale_price or self.list_price, "listing_type_id": self.ml_listing_type})
        self.ml_fee_option_json = json.dumps(listing, ensure_ascii=False, indent=2)
        return True

    def action_ml_select_shipping(self):
        self.ensure_one()
        account = self._get_ml_account()
        account._ml_request("GET", "/users/me")
        self.ml_shipping_mode = self.ml_shipping_mode or "me2"
        return True

    def action_ml_select_warranty(self):
        self.ensure_one()
        self.ml_warranty_type = self.ml_warranty_type or "Garantía del vendedor"
        return True

    def action_ml_sync_from_odoo(self):
        account = self._get_ml_account()
        stats = {"ok": 0, "error": 0}
        for rec in self:
            if not rec.ml_sync_enabled or not rec.ml_item_id:
                continue
            payload = {
                "price": rec.ml_net_price,
                "available_quantity": max(0, rec.ml_publish_qty),
                "status": "active" if rec.ml_sync_active else "paused",
            }
            try:
                account._ml_request("PUT", f"/items/{rec.ml_item_id}", payload=payload)
                rec.ml_last_sync = fields.Datetime.now()
                stats["ok"] += 1
            except Exception as err:
                stats["error"] += 1
                _logger.exception("Error sync Odoo->ML producto %s: %s", rec.display_name, err)
        return stats

    def action_ml_sync_from_ml(self):
        account = self._get_ml_account()
        for rec in self:
            if not rec.ml_item_id:
                continue
            data = account._ml_request("GET", f"/items/{rec.ml_item_id}")
            rec.ml_sale_price = data.get("price") or rec.ml_sale_price
            rec.ml_listing_type = data.get("listing_type_id") or rec.ml_listing_type
            status = data.get("status")
            if status in ("active", "paused", "under_review"):
                rec.ml_publish_state = "published"
            elif status in ("closed", "inactive"):
                rec.ml_publish_state = "deleted"
            rec.ml_last_sync = fields.Datetime.now()
        return True

    def action_ml_publish_product(self):
        account = self._get_ml_account()
        for rec in self:
            if not rec.ml_sync_enabled:
                raise UserError(f"Activa 'Sincronizar con MercadoLibre' en {rec.display_name}.")
            payload = rec._prepare_ml_payload()
            if rec.ml_item_id:
                account._ml_request("PUT", f"/items/{rec.ml_item_id}", payload=payload)
            else:
                created = account._ml_request("POST", "/items", payload=payload)
                rec.ml_item_id = created.get("id")
            rec.ml_publish_state = "published"
            rec.ml_last_sync = fields.Datetime.now()
        return True

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