# -*- coding: utf-8 -*-
import json

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_publish_enabled = fields.Boolean(string="Publicar en MercadoLibre", default=False)
    ml_account_id = fields.Many2one(
        "sce.account",
        string="Cuenta ML",
        domain="[('provider_type', '=', 'mercadolibre')]",
    )

    ml_title = fields.Char(string="Título ML")
    ml_subtitle = fields.Char(string="Subtítulo ML")
    ml_category_id = fields.Char(string="Categoría ML")
    ml_listing_type = fields.Char(string="Tipo de publicación", default="gold_special")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
        default="new",
    )
    ml_brand = fields.Char(string="Marca")
    ml_model = fields.Char(string="Modelo")
    ml_warranty = fields.Char(string="Garantía")
    ml_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Forma de envío",
        default="me2",
    )
    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios ML")
    ml_use_pricelist_price = fields.Boolean(string="Usar lista de precios", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_stock_reserve_qty = fields.Float(string="Stock reservado para Odoo", default=0.0)

    ml_price = fields.Float(string="Precio ML")
    ml_quantity = fields.Float(string="Cantidad ML")
    ml_video = fields.Char(string="Video")
    ml_description_html = fields.Html(string="Descripción HTML")
    ml_attributes_json = fields.Text(string="Atributos JSON")
    ml_required_completion = fields.Float(
        string="% Atributos requeridos",
        compute="_compute_ml_required_completion",
        digits=(16, 2),
    )

    ml_status = fields.Char(string="Estado ML", readonly=True)
    ml_permalink = fields.Char(string="URL publicación", readonly=True)
    ml_item_id = fields.Char(string="ID Publicación", readonly=True)
    ml_publish_date = fields.Datetime(string="Fecha publicación", readonly=True)
    ml_sync_date = fields.Datetime(string="Última sincronización", readonly=True)

    def _get_ml_account(self):
        self.ensure_one()
        account = self.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay una cuenta SCE MercadoLibre activa configurada.")
        return account

    def _effective_title(self):
        self.ensure_one()
        return (self.ml_title or self.name or "").strip()

    def _effective_price(self):
        self.ensure_one()
        if self.ml_manual_price_override and self.ml_price > 0:
            return self.ml_price
        if self.ml_use_pricelist_price and self.ml_pricelist_id:
            try:
                return self.ml_pricelist_id._get_product_price(self, 1.0)
            except Exception:
                return self.list_price
        return self.ml_price if self.ml_price > 0 else self.list_price

    def _effective_qty(self):
        self.ensure_one()
        reserve = max(0.0, self.ml_stock_reserve_qty or 0.0)
        qty_source = self.qty_available
        qty = max(0.0, qty_source - reserve)
        return int(qty)

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
        if self.ml_brand:
            attrs.append({"id": "BRAND", "value_name": self.ml_brand})
        if self.ml_model:
            attrs.append({"id": "MODEL", "value_name": self.ml_model})
        return attrs

    def _collect_ml_pictures(self):
        self.ensure_one()
        pictures = []
        if self.image_1920:
            pictures.append({"source": "data:image/jpeg;base64,%s" % self.image_1920.decode()})

        extra_images = getattr(self, "product_template_image_ids", False)
        if extra_images:
            for extra in extra_images:
                if getattr(extra, "image_1920", False):
                    pictures.append({"source": "data:image/jpeg;base64,%s" % extra.image_1920.decode()})
        return pictures

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

    def _build_ml_payload(self):
        self.ensure_one()
        title = self._effective_title()
        if not title:
            raise UserError("Falta título para publicar en MercadoLibre.")
        price = self._effective_price()
        if price <= 0:
            raise UserError("El precio debe ser mayor a cero.")
        qty = self._effective_qty()

        category = self.ml_category_id or "MLA3530"
        listing_type = self.ml_listing_type or "gold_special"

        payload = {
            "title": title,
            "category_id": category,
            "price": price,
            "currency_id": "ARS",
            "available_quantity": qty,
            "buying_mode": "buy_it_now",
            "condition": self.ml_condition or "new",
            "listing_type_id": listing_type,
            "seller_custom_field": (self.default_code or "").strip() or False,
            "sale_terms": [],
            "pictures": self._collect_ml_pictures(),
            "attributes": self._parse_ml_attributes(),
            "shipping": {"mode": self.ml_shipping_mode or "me2"},
        }

        if self.ml_warranty:
            payload["sale_terms"].append({"id": "WARRANTY_TYPE", "value_name": self.ml_warranty})

        if self.ml_description_html:
            payload["description_plain_text"] = self.ml_description_html

        if self.image_1920:
            payload["image_1920"] = self.image_1920.decode()

        combinations = self._build_variant_combinations()
        if combinations:
            payload["attribute_combinations"] = combinations

        if self.ml_video:
            payload["video_id"] = self.ml_video

        if self.ml_item_id:
            payload["item_id"] = self.ml_item_id

        return payload

    def _get_ml_provider(self, account):
        self.ensure_one()
        if not account:
            raise UserError(
                "No hay cuenta SCE MercadoLibre activa. "
                "Configura una cuenta en el conector base para usar provider unificado."
            )
        return ProviderFactory.get_provider(account)

    def _apply_ml_response(self, response, default_status=False):
        self.ensure_one()
        raw = response.get("raw") if isinstance(response, dict) else {}
        if not isinstance(raw, dict):
            raw = {}
        self.write({
            "ml_item_id": raw.get("id") or response.get("item_id") or self.ml_item_id,
            "ml_status": raw.get("status") or default_status or self.ml_status,
            "ml_permalink": raw.get("permalink") or self.ml_permalink,
            "ml_publish_date": self.ml_publish_date or fields.Datetime.now(),
            "ml_sync_date": fields.Datetime.now(),
        })

    def _compute_ml_required_completion(self):
        for product in self:
            product.ml_required_completion = 0.0
            category_id = (product.ml_category_id or "").strip()
            if not category_id:
                continue
            account = product.ml_account_id or product.env["sce.account"].search(
                [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
                limit=1,
            )
            if not account:
                continue
            try:
                provider = ProviderFactory.get_provider(account)
                req_res = provider.get_category_required_fields(category_id=category_id)
                required = req_res.get("items") if isinstance(req_res, dict) else []
                if not isinstance(required, list):
                    required = []
                req_ids = {(a.get("id") or "").strip() for a in required if isinstance(a, dict)}
                req_ids.discard("")
                total = len(req_ids)
                if total == 0:
                    product.ml_required_completion = 100.0
                    continue
                attrs = []
                raw = product.ml_attributes_json or ""
                if raw:
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            attrs = [a for a in parsed if isinstance(a, dict)]
                    except Exception:
                        attrs = []
                provided = set()
                for a in attrs:
                    aid = (a.get("id") or "").strip()
                    if not aid:
                        continue
                    val = (a.get("value_name") or "").strip()
                    if aid in req_ids and val:
                        provided.add(aid)
                product.ml_required_completion = (len(provided) * 100.0) / total
            except Exception:
                product.ml_required_completion = 0.0

    def action_open_ml_attribute_editor_wizard(self):
        self.ensure_one()
        if not (self.ml_category_id or "").strip():
            raise UserError("Primero define una categoría ML.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.attribute.editor.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }

    def action_open_ml_publish_config_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.config.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_product_tmpl_id": self.id},
        }

    def action_open_ml_category_search_wizard(self):
        self.ensure_one()
        account = self._get_ml_account()
        wizard = self.env["ml.category.search.wizard"].create(
            {
                "product_tmpl_id": self.id,
                "account_id": account.id,
                "query": self.ml_title or self.name or "",
                "selected_category_id": self.ml_category_id or "",
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
            issues = []
            title = (product.ml_title or product.name or "").strip()
            if not title:
                issues.append("Falta título.")
            if not (product.ml_category_id or "").strip():
                issues.append("Falta categoría ML.")
            if product._effective_price() <= 0:
                issues.append("El precio debe ser mayor a cero.")
            if product._effective_qty() < 0:
                issues.append("El stock no puede ser negativo.")
            if not product.ml_account_id and not self.env["sce.account"].search(
                [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
                limit=1,
            ):
                issues.append("No hay cuenta SCE MercadoLibre activa.")
            if not product._collect_ml_pictures():
                issues.append("No hay imágenes para publicar.")
            if not (product.ml_brand or "").strip():
                issues.append("Falta marca.")
            if not (product.ml_model or "").strip():
                issues.append("Falta modelo.")

            if issues:
                raise UserError("Validación de publicación ML:\n- " + "\n- ".join(issues))

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
            account = product._get_ml_account()
            provider = product._get_ml_provider(account)
            payload = product._build_ml_payload()

            if product.ml_item_id:
                result = provider.update_product(payload)
            else:
                result = provider.publish_product(payload)

            product._apply_ml_response(result)

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
        return self.action_publish_ml()

    def action_pause_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            provider = product._get_ml_provider(account)
            provider.update_product({"item_id": product.ml_item_id, "status": "paused", **product._build_ml_payload()})
            product.write({"ml_status": "paused", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_reactivate_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            provider = product._get_ml_provider(account)
            provider.update_product({"item_id": product.ml_item_id, "status": "active", **product._build_ml_payload()})
            product.write({"ml_status": "active", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_close_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            provider = product._get_ml_provider(account)
            provider.delete_product({"item_id": product.ml_item_id})
            product.write({"ml_status": "closed", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_sync_from_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            provider = product._get_ml_provider(account)
            result = provider.sync({
                "operation": "import_item",
                "payload": {"item_id": product.ml_item_id},
            })
            item = result.get("item") if isinstance(result, dict) else {}
            if not isinstance(item, dict):
                item = {}
            vals = {
                "ml_status": item.get("status") or product.ml_status,
                "ml_permalink": item.get("permalink") or product.ml_permalink,
                "ml_item_id": item.get("id") or product.ml_item_id,
                "ml_sync_date": fields.Datetime.now(),
            }
            if item.get("price"):
                vals["ml_price"] = float(item.get("price"))
            if item.get("available_quantity") is not None:
                vals["ml_quantity"] = float(item.get("available_quantity"))
            product.write(vals)
        return True

    def action_view_ml(self):
        self.ensure_one()
        if not self.ml_permalink:
            raise UserError("Este producto no tiene URL de publicación.")
        return {
            "type": "ir.actions.act_url",
            "url": self.ml_permalink,
            "target": "new",
        }