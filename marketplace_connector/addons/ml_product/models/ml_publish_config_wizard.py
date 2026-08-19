# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory


_logger = logging.getLogger(__name__)


class MlPublishConfigWizard(models.TransientModel):
    _name = "ml.publish.config.wizard"
    _description = "Configuración UX de publicación MercadoLibre"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    account_id = fields.Many2one("sce.account", string="Cuenta ML", readonly=True)
    publication_id = fields.Many2one(
        "marketplace.publication", string="Publicación", readonly=True, ondelete="cascade"
    )

    ml_listing_type_id = fields.Many2one("ml.listing.type", string="Tipo de publicación")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
    )
    ml_warranty = fields.Char(string="Garantía")
    ml_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Forma de envío",
        default="me2",
    )

    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    ml_use_pricelist_price = fields.Boolean(string="Usar precio desde lista", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_price = fields.Float(string="Precio ML")

    ml_stock_reserve_qty = fields.Float(string="Stock reservado para Odoo", default=0.0)

    def _raise_if_access_denied_response(self, payload, operation):
        if isinstance(payload, str):
            text = payload.lower()
            if "<html" in text and "access denied" in text:
                _logger.error(
                    "Access Denied detectado en operación ML '%s' para account_id=%s",
                    operation,
                    self.account_id.id if self.account_id else False,
                )
                raise UserError(
                    "Acceso denegado por el servicio remoto. "
                    "Revisa permisos/sesión de Odoo.sh y credenciales de la cuenta ML."
                )

    def _compute_suggested_price(self, product, pricelist):
        if not product:
            return 0.0
        if pricelist:
            try:
                return float(pricelist._get_product_price(product, 1.0) or 0.0)
            except Exception:
                return float(product.list_price or 0.0)
        return float(product.ml_price or product.list_price or 0.0)

    @api.onchange("ml_pricelist_id", "ml_use_pricelist_price", "ml_manual_price_override")
    def _onchange_ml_price_behavior(self):
        for wizard in self:
            if not wizard.product_tmpl_id:
                continue
            if wizard.ml_manual_price_override:
                if not wizard.ml_price:
                    wizard.ml_price = wizard.product_tmpl_id.ml_price or wizard.product_tmpl_id.list_price
            elif wizard.ml_use_pricelist_price:
                wizard.ml_price = wizard._compute_suggested_price(wizard.product_tmpl_id, wizard.ml_pricelist_id)
            else:
                wizard.ml_price = wizard.product_tmpl_id.ml_price or wizard.product_tmpl_id.list_price

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        product_id = self.env.context.get("default_product_tmpl_id")
        if not product_id:
            return vals
        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            return vals

        account = product.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay cuenta SCE MercadoLibre activa configurada.")

        provider = ProviderFactory.get_provider(account)
        listing_items = []

        try:
            if hasattr(provider, "get_listing_types"):
                listing_res = provider.get_listing_types()
                self._raise_if_access_denied_response(listing_res, "get_listing_types")
                if isinstance(listing_res, dict):
                    listing_items = listing_res.get("items")
                else:
                    _logger.warning(
                        "Respuesta inesperada en get_listing_types para account_id=%s: %s",
                        account.id,
                        type(listing_res).__name__,
                    )
                    listing_items = []
            elif hasattr(provider, "sync"):
                sync_res = provider.sync({"operation": "get_listing_types", "payload": {}})
                self._raise_if_access_denied_response(sync_res, "sync:get_listing_types")
                if isinstance(sync_res, dict):
                    listing_items = sync_res.get("items")
                else:
                    _logger.warning(
                        "Respuesta inesperada en sync(get_listing_types) para account_id=%s: %s",
                        account.id,
                        type(sync_res).__name__,
                    )
                    listing_items = []
        except Exception:
            _logger.exception("Error cargando listing types para account_id=%s", account.id)
            listing_items = []

        if not isinstance(listing_items, list) or not listing_items:
            listing_items = [
                {"id": "gold_special", "name": "Clásica", "status": "active"},
                {"id": "gold_pro", "name": "Premium", "status": "active"},
            ]

        listing_type_model = self.env["ml.listing.type"]
        existing_types = listing_type_model.search([("account_id", "=", account.id)])
        existing_map = {rec.listing_type_id: rec for rec in existing_types}

        for item in listing_items:
            if not isinstance(item, dict):
                continue
            ltid = (item.get("id") or "").strip()
            if not ltid:
                continue
            vals = {
                "account_id": account.id,
                "listing_type_id": ltid,
                "name": (item.get("name") or ltid).strip(),
                "status": item.get("status") or "",
            }
            rec = existing_map.get(ltid)
            if rec:
                rec.write({"name": vals["name"], "status": vals["status"]})
            else:
                try:
                    listing_type_model.create(vals)
                except Exception:
                    _logger.warning(
                        "Posible concurrencia/duplicado creando ml.listing.type account_id=%s listing_type_id=%s",
                        account.id,
                        ltid,
                    )
                    rec_retry = listing_type_model.search(
                        [("account_id", "=", account.id), ("listing_type_id", "=", ltid)],
                        limit=1,
                    )
                    if rec_retry:
                        rec_retry.write({"name": vals["name"], "status": vals["status"]})
                    else:
                        raise

        selected_listing = self.env["ml.listing.type"].search(
            [("account_id", "=", account.id), ("listing_type_id", "=", (product.ml_listing_type or "").strip())],
            limit=1,
        )
        publication = self.env["marketplace.publication"].browse(
            self.env.context.get("default_publication_id")
        ).exists()
        if not publication:
            publication = self.env["marketplace.publication"].search(
                [
                    ("product_tmpl_id", "=", product.id),
                    ("account_id", "=", account.id),
                ],
                limit=1,
            )

        suggested_price = self._compute_suggested_price(product, product.ml_pricelist_id if product.ml_use_pricelist_price else False)

        vals.update(
            {
                "product_tmpl_id": product.id,
                "account_id": account.id,
                "ml_listing_type_id": selected_listing.id if selected_listing else False,
                "ml_condition": product.ml_condition,
                "ml_warranty": product.ml_warranty,
                "ml_shipping_mode": product.ml_shipping_mode or "me2",
                "ml_pricelist_id": product.ml_pricelist_id.id if product.ml_pricelist_id else False,
                "ml_use_pricelist_price": product.ml_use_pricelist_price,
                "ml_manual_price_override": product.ml_manual_price_override,
                "ml_price": product.ml_price if product.ml_manual_price_override else suggested_price,
                "ml_stock_reserve_qty": product.ml_stock_reserve_qty,
                "publication_id": publication.id if publication else False,
            }
        )
        return vals

    def action_apply(self):
        self.ensure_one()
        if self.publication_id:
            self.publication_id.write(
                {
                    "account_id": self.account_id.id,
                    "listing_type": self.ml_listing_type_id.listing_type_id if self.ml_listing_type_id else "gold_special",
                    "condition": self.ml_condition or "new",
                    "shipping_mode": self.ml_shipping_mode or "me2",
                    "pricelist_id": self.ml_pricelist_id.id if self.ml_pricelist_id else False,
                    "use_pricelist_price": bool(self.ml_use_pricelist_price),
                    "manual_price_override": bool(self.ml_manual_price_override),
                    "price": self.ml_price if self.ml_manual_price_override else self.product_tmpl_id.list_price,
                    "stock_reserve_qty": max(0.0, self.ml_stock_reserve_qty or 0.0),
                    "state": "pricing",
                }
            )
        self.product_tmpl_id.write(
            {
                "ml_listing_type": self.ml_listing_type_id.listing_type_id if self.ml_listing_type_id else "gold_special",
                "ml_condition": self.ml_condition or "new",
                "ml_warranty": self.ml_warranty or False,
                "ml_shipping_mode": self.ml_shipping_mode or "me2",
                "ml_pricelist_id": self.ml_pricelist_id.id if self.ml_pricelist_id else False,
                "ml_use_pricelist_price": bool(self.ml_use_pricelist_price),
                "ml_manual_price_override": bool(self.ml_manual_price_override),
                "ml_price": self.ml_price if self.ml_manual_price_override else self.product_tmpl_id.ml_price,
                "ml_stock_reserve_qty": max(0.0, self.ml_stock_reserve_qty or 0.0),
            }
        )
        return {"type": "ir.actions.act_window_close"}