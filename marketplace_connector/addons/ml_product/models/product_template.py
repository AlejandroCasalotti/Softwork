# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_publish_enabled = fields.Boolean(string="Publicar en MercadoLibre", default=False)
    ml_account_id = fields.Many2one(
        "sce.account",
        string="Cuenta ML",
        domain="[('provider_type', '=', 'mercadolibre')]",
    )

    ml_title = fields.Char(string="Título ML")
    ml_category_id = fields.Char(string="Categoría ML")
    ml_listing_type = fields.Char(string="Tipo de publicación", default="gold_special")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
        default="new",
    )
    ml_brand = fields.Char(string="Marca")
    ml_model = fields.Char(string="Modelo")
    ml_family_name_id = fields.Char(
        string="Familia/Línea de Producto", help="Requerido por MercadoLibre para muchas categorías"
    )
    ml_warranty = fields.Char(string="Garantía")
    ml_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Forma de envío",
        default="me2",
    )
    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios ML")
    ml_price_uom_id = fields.Many2one("uom.uom", string="UoM de precio ML")
    ml_use_pricelist_price = fields.Boolean(string="Usar lista de precios", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_stock_reserve_qty = fields.Float(string="Stock reservado para Odoo", default=0.0)

    ml_price = fields.Float(string="Precio ML")
    ml_description_html = fields.Html(string="Descripción HTML")
    ml_attributes_json = fields.Text(string="Atributos JSON")
    ml_sale_terms_json = fields.Text(string="Sale Terms JSON")
    ml_pictures_json = fields.Text(string="Pictures JSON")
    ml_status = fields.Char(string="Estado ML", readonly=True)
    ml_permalink = fields.Char(string="URL publicación", readonly=True)
    ml_item_id = fields.Char(string="ID Publicación", readonly=True)
    ml_catalog_managed = fields.Boolean(string="Título administrado por catálogo", readonly=True)

    def _get_ml_account(self):
        self.ensure_one()
        account = self.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay una cuenta SCE MercadoLibre activa configurada.")
        return account

    def _get_or_create_ml_publication(self):
        self.ensure_one()
        account = self._get_ml_account()
        publication = self.env["marketplace.publication"].search(
            [("product_tmpl_id", "=", self.id), ("account_id", "=", account.id)],
            limit=1,
        )
        if not publication:
            publication = self.env["marketplace.publication"].create(
                {
                    "product_tmpl_id": self.id,
                    "account_id": account.id,
                    "title": self.ml_title or self.name or "",
                    "category_ref": self.ml_category_id or "",
                    "listing_type": self.ml_listing_type or "gold_special",
                    "condition": self.ml_condition or "new",
                    "shipping_mode": self.ml_shipping_mode or "me2",
                }
            )
        return publication

    def _effective_title(self):
        self.ensure_one()
        return (self.ml_title or self.name or "").strip()

    def _effective_price(self):
        self.ensure_one()
        target_uom = self.ml_price_uom_id or self.uom_id
        base_price = 0.0
        if self.ml_use_pricelist_price and self.ml_pricelist_id:
            try:
                base_price = self.ml_pricelist_id._get_product_price(self, 1.0, uom=self.uom_id) or 0.0
            except Exception:
                pass
        if not base_price:
            base_price = self.ml_price if self.ml_price > 0 else self.list_price
        if self.ml_manual_price_override and self.ml_price > 0:
            return self.ml_price
        if target_uom == self.uom_id:
            return base_price
        try:
            units_in_base = target_uom._compute_quantity(1.0, self.uom_id, round=False)
            return base_price * units_in_base
        except Exception:
            return base_price

    def _effective_qty(self):
        self.ensure_one()
        reserve = max(0.0, self.ml_stock_reserve_qty or 0.0)
        qty_source = self.qty_available
        qty = max(0.0, qty_source - reserve)
        return int(qty)

    def _normalize_ml_value(self, value):
        text = (value or "").strip()
        if not text:
            return text
        text = text.replace(",", ".")
        text = re.sub(r"\bm2\b", "m²", text, flags=re.IGNORECASE)
        text = re.sub(r"\bcm2\b", "cm²", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmm2\b", "mm²", text, flags=re.IGNORECASE)
        text = re.sub(r"\bin2\b", "in²", text, flags=re.IGNORECASE)
        return text

    def _parse_ml_attributes(self):
        self.ensure_one()
        attrs = []
        raw = self.ml_attributes_json
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    attrs = [a for a in parsed if isinstance(a, dict)]
            except Exception:
                attrs = []

        normalized = []
        for a in attrs:
            aid = (a.get("id") or "").strip()
            if not aid:
                continue
            item = {"id": aid}
            if a.get("value_id"):
                item["value_id"] = (a.get("value_id") or "").strip()
            if a.get("value_name"):
                item["value_name"] = self._normalize_ml_value(a.get("value_name"))
            normalized.append(item)

        if self.ml_brand:
            normalized.append({"id": "BRAND", "value_name": self._normalize_ml_value(self.ml_brand)})
        if self.ml_model:
            normalized.append({"id": "MODEL", "value_name": self._normalize_ml_value(self.ml_model)})
        return normalized

    def _collect_ml_pictures(self, account=None):
        self.ensure_one()
        pictures = []

        raw_pictures = (self.ml_pictures_json or "").strip()
        if raw_pictures:
            try:
                parsed = json.loads(raw_pictures)
                if isinstance(parsed, list):
                    for item in parsed:
                        if not isinstance(item, dict):
                            continue
                        source = (item.get("source") or "").strip()
                        if self._is_valid_ml_picture_source(source):
                            pictures.append({"source": source})
            except Exception:
                pictures = []

        if pictures:
            return pictures

        # No hay imágenes manuales/sincronizadas: usamos la imagen principal y la galería de Odoo
        return self._collect_odoo_image_sources(account=account)

    @staticmethod
    def _is_valid_ml_picture_source(source):
        # MercadoLibre exige source URL http/https pública y de hasta 1024 caracteres
        s = (source or "").strip()
        return bool(s and s.startswith(("http://", "https://")) and len(s) <= 1024)

    def _get_ml_public_base_url(self, account=None):
        self.ensure_one()
        account = account or self.ml_account_id
        if account and (account.odoo_base_url or "").strip():
            return account.odoo_base_url.strip().rstrip("/")
        return (self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "").strip().rstrip("/")

    def _collect_odoo_image_sources(self, account=None):
        """URLs públicas (http/https) de la imagen principal y galería del producto en Odoo."""
        self.ensure_one()
        base_url = self._get_ml_public_base_url(account=account)
        if not base_url:
            return []

        sources = []
        if self.image_1920:
            url = f"{base_url}/web/image/product.template/{self.id}/image_1920?unique={self.write_date or fields.Datetime.now()}"
            if self._is_valid_ml_picture_source(url):
                sources.append({"source": url})

        gallery = getattr(self, "product_template_image_ids", False)
        for image in (gallery.sorted("sequence") if gallery else []):
            url = f"{base_url}/web/image/product.image/{image.id}/image_1920?unique={image.write_date or fields.Datetime.now()}"
            if self._is_valid_ml_picture_source(url):
                sources.append({"source": url})

        return sources

    def _build_variant_combinations(self):
        self.ensure_one()
        combinations = []
        variants = self.product_variant_ids.filtered(lambda v: v.active)
        if len(variants) <= 1:
            return combinations
        for variant in variants:
            values = []
            for pav in variant.product_template_attribute_value_ids:
                attr = pav.attribute_id
                if not attr or not pav.product_attribute_value_id:
                    continue
                values.append({
                    "name": attr.name,
                    "value_name": pav.product_attribute_value_id.name,
                })
            combinations.append({
                "sku": variant.default_code or "",
                "available_quantity": int(max(0, variant.qty_available)),
                "price": variant.lst_price or self._effective_price(),
                "attributes": values,
            })
        return combinations

    def action_modify_ml_listing(self):
        self.ensure_one()
        publication = self._get_or_create_ml_publication()
        if not publication.external_id and self.ml_item_id:
            publication.write({"external_id": self.ml_item_id})
        if not publication.external_id:
            raise UserError("Primero publica el producto en MercadoLibre.")
        self.env["marketplace.publication.service"].refresh_for_edit(publication)
        return publication.action_open_ml_publish_assistant()

    def action_open_ml_attribute_editor_wizard(self):
        self.ensure_one()
        publication = self._get_or_create_ml_publication()
        if not (publication.category_ref or self.ml_category_id or "").strip():
            raise UserError("Primero define una categoría ML.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.attribute.editor.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
                "default_publication_id": publication.id,
            },
        }

    def action_open_ml_publish_config_wizard(self):
        self.ensure_one()
        publication = self._get_or_create_ml_publication()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.config.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
                "default_publication_id": publication.id,
            },
        }

    def action_open_ml_publish_assistant_wizard(self):
        self.ensure_one()
        publication = self._get_or_create_ml_publication()
        return {
            "type": "ir.actions.act_window",
            "res_model": "marketplace.publication",
            "view_mode": "form",
            "res_id": publication.id,
            "target": "current",
        }

    def action_open_ml_category_search_wizard(self):
        self.ensure_one()
        account = self._get_ml_account()
        publication = self._get_or_create_ml_publication()
        wizard = self.env["ml.category.search.wizard"].create(
            {
                "product_tmpl_id": self.id,
                "publication_id": publication.id,
                "account_id": account.id,
                "query": self.ml_title or self.name or "",
                "selected_category_id": publication.category_ref or self.ml_category_id or "",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.category.search.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def action_validate_ml_listing(self):
        for product in self:
            publication = product._get_or_create_ml_publication()
            publication._validate_for_operation()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Validación MercadoLibre",
                "message": "Validación OK. El producto está listo para publicar.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_publish_ml(self):
        for product in self:
            if not product.ml_publish_enabled:
                continue
            publication = product._get_or_create_ml_publication()
            if product.ml_item_id:
                publication.write({"external_id": product.ml_item_id})
                product.env["marketplace.publication.service"].enqueue(publication, "update")
            else:
                product.env["marketplace.publication.service"].enqueue(publication, "publish")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "MercadoLibre",
                "message": "Producto publicado/actualizado correctamente.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_update_ml(self):
        for product in self:
            if not product.ml_item_id:
                raise UserError("Primero publica el producto en MercadoLibre.")
        return self.action_publish_ml()

    def action_pause_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            publication = product._get_or_create_ml_publication()
            publication.write({"external_id": product.ml_item_id, "external_status": "paused"})
            product.env["marketplace.publication.service"].enqueue(publication, "update")
        return True

    def action_reactivate_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            publication = product._get_or_create_ml_publication()
            publication.write({"external_id": product.ml_item_id, "external_status": "active"})
            product.env["marketplace.publication.service"].enqueue(publication, "update")
        return True

    def action_close_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            publication = product._get_or_create_ml_publication()
            publication.write({"external_id": product.ml_item_id})
            product.env["marketplace.publication.service"].enqueue(publication, "delete")
        return True

    def _sync_price_stock_to_ml(self):
        for product in self:
            if not product.ml_publish_enabled or not product.ml_item_id:
                continue
            try:
                publication = product._get_or_create_ml_publication()
                publication.write(
                    {
                        "external_id": product.ml_item_id,
                        "title": product._effective_title(),
                        "price": product._effective_price(),
                        "stock_reserve_qty": max(0.0, product.ml_stock_reserve_qty or 0.0),
                        "use_pricelist_price": bool(product.ml_use_pricelist_price),
                        "manual_price_override": bool(product.ml_manual_price_override),
                    }
                )
                self.env["marketplace.publication.service"].enqueue(publication, "update")
            except Exception:
                _logger.exception(
                    "No se pudo encolar sincronización ML para product_tmpl_id=%s",
                    product.id,
                )
                continue

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("ml_skip_bidirectional_sync"):
            sync_trigger_fields = {
                "list_price",
                "ml_price",
                "ml_stock_reserve_qty",
                "ml_use_pricelist_price",
                "ml_manual_price_override",
                "ml_pricelist_id",
                "ml_publish_enabled",
                "ml_item_id",
            }
            for rec, vals in zip(records, vals_list):
                if any(field in vals for field in sync_trigger_fields):
                    rec._sync_price_stock_to_ml()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("ml_skip_bidirectional_sync"):
            return res

        sync_trigger_fields = {
            "list_price",
            "ml_price",
            "ml_stock_reserve_qty",
            "ml_use_pricelist_price",
            "ml_manual_price_override",
            "ml_pricelist_id",
            "ml_publish_enabled",
            "ml_item_id",
        }
        if any(field in vals for field in sync_trigger_fields):
            self._sync_price_stock_to_ml()
        return res

    def action_sync_price_stock_ml(self):
        self._sync_price_stock_to_ml()
        return True

    def action_sync_from_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            publication = product._get_or_create_ml_publication()
            publication.write({"external_id": product.ml_item_id})
            self.env["marketplace.publication.service"].enqueue(publication, "sync")
        return True

    def action_diagnose_ml_connection(self):
        self.ensure_one()
        account = self._get_ml_account()
        try:
            response = self.env["marketplace.publication.service"].diagnose_account(account)
            summary = response.get("status") or response.get("message") or "Conexión ML OK"

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Diagnóstico conexión ML",
                    "message": (
                        f"{summary}\n"
                        f"Cuenta: {account.display_name} (id={account.id})\n"
                        "Operación: health"
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }

        except UserError:
            raise
        except Exception as e:
            _logger.exception(
                "Diagnóstico ML error product_id=%s account_id=%s",
                self.id,
                account.id if account else False,
            )
            raise UserError(
                "Diagnóstico ML falló.\n"
                f"Cuenta: {account.display_name} (id={account.id})\n"
                "Operación: health\n"
                f"Detalle: {str(e)}"
            )

    def action_view_ml(self):
        self.ensure_one()
        publication = self._get_or_create_ml_publication()
        if not publication.external_url and self.ml_permalink:
            publication.write({"external_url": self.ml_permalink})
        if not publication.external_url:
            raise UserError("Este producto no tiene URL de publicación.")
        return {
            "type": "ir.actions.act_url",
            "url": publication.external_url,
            "target": "new",
        }