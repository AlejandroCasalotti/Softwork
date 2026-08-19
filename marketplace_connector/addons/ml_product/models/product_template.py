# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

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
    ml_quantity = fields.Float(string="Cantidad ML")
    ml_video = fields.Char(string="Video")
    ml_description_html = fields.Html(string="Descripción HTML")
    ml_attributes_json = fields.Text(string="Atributos JSON")
    ml_sale_terms_json = fields.Text(string="Sale Terms JSON")
    ml_pictures_json = fields.Text(string="Pictures JSON")
    ml_required_completion = fields.Float(
        string="% Atributos requeridos",
        compute="_compute_ml_required_completion",
        digits=(16, 2),
    )

    ml_status = fields.Char(string="Estado ML", readonly=True)
    ml_permalink = fields.Char(string="URL publicación", readonly=True)
    ml_item_id = fields.Char(string="ID Publicación", readonly=True)
    ml_catalog_managed = fields.Boolean(string="Título administrado por catálogo", readonly=True)
    ml_listing_cost_summary = fields.Text(string="Cargo por vender y cuotas ML", readonly=True)
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
        if self.ml_manual_price_override and self.ml_price > 0:
            return self.ml_price
        if self.ml_use_pricelist_price and self.ml_pricelist_id:
            try:
                return self.ml_pricelist_id._get_product_price(
                    self, 1.0, uom=self.ml_price_uom_id or self.uom_id
                )
            except Exception:
                pass
        source_uom = self.uom_id
        target_uom = self.ml_price_uom_id or source_uom
        if source_uom and target_uom:
            try:
                return source_uom._compute_price(self.list_price, target_uom)
            except Exception:
                pass
        return self.ml_price if self.ml_price > 0 else self.list_price

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

    def _validate_ml_sale_terms(self):
        self.ensure_one()
        raw = (self.ml_sale_terms_json or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            raise UserError("Sale Terms JSON inválido: debe ser JSON válido.")

        if not isinstance(parsed, list):
            raise UserError("Sale Terms JSON inválido: debe ser una lista de objetos.")

        terms = []
        for term in parsed:
            if not isinstance(term, dict):
                raise UserError("Sale Terms JSON inválido: cada elemento debe ser un objeto.")
            term_id = (term.get("id") or "").strip()
            if not term_id:
                continue
            clean = {"id": term_id}
            if (term.get("value_id") or "").strip():
                clean["value_id"] = (term.get("value_id") or "").strip()
            if (term.get("value_name") or "").strip():
                clean["value_name"] = (term.get("value_name") or "").strip()
            if isinstance(term.get("value_struct"), dict):
                clean["value_struct"] = term.get("value_struct")
            terms.append(clean)
        return terms

    def _filter_ml_attributes_by_category(self, category_id, attrs):
        self.ensure_one()
        if not category_id:
            return attrs
        account = self._get_ml_account()
        try:
            provider = ProviderFactory.get_provider(account)
            req_res = provider.get_category_required_fields(category_id=category_id)
            required = req_res.get("items") if isinstance(req_res, dict) else []
            if not isinstance(required, list):
                required = []
            allowed_ids = {(x.get("id") or "").strip() for x in required if isinstance(x, dict)}
            allowed_ids.discard("")
            if not allowed_ids:
                return attrs
            filtered = [a for a in attrs if (a.get("id") or "").strip() in allowed_ids]
            required_ids = {rid for rid in allowed_ids}
            present_ids = {(a.get("id") or "").strip() for a in filtered}
            missing = sorted(required_ids - present_ids)
            if missing:
                _logger.info("Atributos requeridos ML no presentes para %s: %s", category_id, ", ".join(missing))
            # BRAND y MODEL pueden no venir en los metadatos de categoría.
            special_attrs = {"BRAND", "MODEL"}
            for attr in attrs:
                aid = (attr.get("id") or "").strip()
                if aid in special_attrs and aid not in present_ids:
                    filtered.append(attr)

            return filtered
        except Exception:
            _logger.exception("No se pudo filtrar atributos por categoría ML")
            return attrs

    def _build_ml_payload(self):
        self.ensure_one()
        title = self._effective_title()
        if not title:
            raise UserError("Falta título para publicar en MercadoLibre.")
        price = round(self._effective_price(), 2)
        if price <= 0:
            raise UserError("El precio debe ser mayor a cero.")
        qty = self._effective_qty()

        category = self.ml_category_id or "MLA3530"
        listing_type = self.ml_listing_type or "gold_special"

        sale_terms = self._validate_ml_sale_terms()
        attrs = self._parse_ml_attributes()
        try:
            account = self._get_ml_account()
            provider = ProviderFactory.get_provider(account)
            req_res = provider.get_category_required_fields(category_id=category)
            required = req_res.get("items") if isinstance(req_res, dict) else []
            if not isinstance(required, list):
                required = []
            allowed_sale_terms = {(x.get("id") or "").strip() for x in required if isinstance(x, dict)}
            allowed_sale_terms.discard("")
            sale_terms = [t for t in sale_terms if (t.get("id") or "").strip() in allowed_sale_terms]
            attrs = self._filter_ml_attributes_by_category(category, attrs)
        except Exception:
            _logger.exception("No se pudo filtrar sale_terms/attributes por categoría ML; se conserva payload original.")

        pictures = []
        for pic in self._collect_ml_pictures():
            source = (pic.get("source") or "").strip() if isinstance(pic, dict) else ""
            if self._is_valid_ml_picture_source(source):
                pictures.append({"source": source})
            else:
                _logger.warning(
                    "Foto descartada para publicación ML (source inválido/excede 1024 caracteres) product_tmpl_id=%s",
                    self.id,
                )

        payload = {
            "title": title,
            "category_id": category,
            "price": price,
            "currency_id": "ARS",
            "available_quantity": qty,
            "buying_mode": "buy_it_now",
            "condition": self.ml_condition or "new",
            "listing_type_id": listing_type,
            "family_name": (self.ml_family_name_id or "").strip(),
            "seller_custom_field": (self.default_code or "").strip() or False,
            "sale_terms": sale_terms,
            "pictures": pictures,
            "attributes": attrs,
            "shipping": {"mode": self.ml_shipping_mode or "me2"},
        }

        if self.ml_warranty:
            existing_term_ids = {(t.get("id") or "").strip() for t in payload["sale_terms"] if isinstance(t, dict)}
            if "WARRANTY_TYPE" not in existing_term_ids:
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
        vals = {
            "ml_item_id": raw.get("id") or response.get("item_id") or self.ml_item_id,
            "ml_status": raw.get("status") or default_status or self.ml_status,
            "ml_permalink": raw.get("permalink") or self.ml_permalink,
            "ml_catalog_managed": bool(response.get("catalog_managed", self.ml_catalog_managed)),
            "ml_publish_date": self.ml_publish_date or fields.Datetime.now(),
            "ml_sync_date": fields.Datetime.now(),
        }
        if raw.get("title"):
            vals["ml_title"] = raw["title"]
        self.write(vals)

    def action_modify_ml_listing(self):
        self.ensure_one()
        if not self.ml_item_id:
            raise UserError("Primero publica el producto en MercadoLibre.")
        account = self._get_ml_account()
        provider = self._get_ml_provider(account)
        result = provider.get_item(self.ml_item_id)
        item = result.get("item") if isinstance(result, dict) else {}
        if not isinstance(item, dict):
            raise UserError("MercadoLibre no devolvió los datos de la publicación.")

        attrs = item.get("attributes") if isinstance(item.get("attributes"), list) else []
        pictures = item.get("pictures") if isinstance(item.get("pictures"), list) else []
        cost_summary = "MercadoLibre no informó cargos ni cuotas para esta publicación."
        if hasattr(provider, "get_listing_prices") and item.get("price"):
            try:
                quote = provider.get_listing_prices(
                    category_id=item.get("category_id") or self.ml_category_id,
                    price=item["price"],
                    listing_type_id=item.get("listing_type_id") or self.ml_listing_type,
                )
                quotes = quote.get("items") if isinstance(quote, dict) else []
                lines = []
                for quote_item in quotes if isinstance(quotes, list) else []:
                    details = quote_item.get("sale_fee_details") if isinstance(quote_item.get("sale_fee_details"), dict) else {}
                    fee = quote_item.get("sale_fee_amount", details.get("gross_amount"))
                    installment = quote_item.get("installments") or {}
                    installment_text = "Sin cuotas informadas"
                    if isinstance(installment, dict) and installment:
                        installment_text = (
                            f"{installment.get('quantity') or 0} cuotas de $ {installment.get('amount') or 0} "
                            f"(tasa {installment.get('rate') or 0}%)"
                        )
                    lines.append(f"Comisión: $ {fee if fee is not None else 0}. {installment_text}.")
                if lines:
                    cost_summary = "\n".join(lines)
            except Exception:
                _logger.exception("No se pudo consultar la cotización ML para product_tmpl_id=%s", self.id)
        vals = {
            "ml_title": item.get("title") or self.ml_title,
            "ml_price": float(item["price"]) if item.get("price") is not None else self.ml_price,
            "ml_quantity": float(item["available_quantity"]) if item.get("available_quantity") is not None else self.ml_quantity,
            "ml_status": item.get("status") or self.ml_status,
            "ml_permalink": item.get("permalink") or self.ml_permalink,
            "ml_attributes_json": json.dumps(attrs, ensure_ascii=False),
            "ml_pictures_json": json.dumps(pictures, ensure_ascii=False),
            "ml_catalog_managed": bool(item.get("catalog_product_id")) or self.ml_catalog_managed,
            "ml_listing_cost_summary": cost_summary,
            "ml_sync_date": fields.Datetime.now(),
        }
        self.with_context(ml_skip_bidirectional_sync=True).write(vals)

        return self.action_open_ml_publish_assistant_wizard()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

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
        publication = self._get_or_create_ml_publication()
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

    def _validate_ml_required_attributes(self, attrs):
        self.ensure_one()
        category_id = (self.ml_category_id or "").strip()
        if not category_id:
            return []

        issues = []
        account = self.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            return []

        try:
            provider = ProviderFactory.get_provider(account)
            req_res = provider.get_category_required_fields(category_id=category_id)
            required = req_res.get("items") if isinstance(req_res, dict) else []
            if not isinstance(required, list):
                required = []
            req_ids = {(a.get("id") or "").strip() for a in required if isinstance(a, dict)}
            req_ids.discard("")
            attr_map = {(a.get("id") or "").strip(): a for a in attrs if isinstance(a, dict)}
            for rid in req_ids:
                v = attr_map.get(rid, {})
                has_value = bool((v.get("value_id") or "").strip() or (v.get("value_name") or "").strip())
                if not has_value:
                    issues.append(f"Falta atributo requerido ML: {rid}")
        except Exception:
            return issues
        return issues

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
            pics = product._collect_ml_pictures()
            if not pics:
                issues.append("No hay imágenes públicas válidas para publicar (source debe ser URL http/https <= 1024).")
            else:
                for p in pics:
                    src = (p.get("source") or "").strip()
                    if not src.startswith(("http://", "https://")) or len(src) > 1024:
                        issues.append("Hay imágenes con source inválido para MercadoLibre.")
                        break
            if not (product.ml_brand or "").strip():
                issues.append("Falta marca.")
            if not (product.ml_model or "").strip():
                issues.append("Falta modelo.")

            attrs = product._parse_ml_attributes()
            issues.extend(product._validate_ml_required_attributes(attrs))

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

            try:
                if product.ml_item_id:
                    result = provider.update_product(payload)
                else:
                    result = provider.publish_product(payload)
            except UserError as e:
                msg = str(e)
                if (
                    (product.ml_shipping_mode or "me2") == "me2"
                    and (
                        "shipping.lost_me2" in msg
                        or "shipping.lost_me1" in msg
                        or "shipping.lost_me2_by_intersected_logistics" in msg
                        or "shipping.lost_me1_by_user" in msg
                    )
                ):
                    payload["shipping"] = {"mode": "custom"}
                    if product.ml_item_id:
                        result = provider.update_product(payload)
                    else:
                        result = provider.publish_product(payload)
                else:
                    raise

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
        for product in self:
            if not product.ml_item_id:
                raise UserError("Primero publica el producto en MercadoLibre.")
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
        provider = self._get_ml_provider(account)

        operation = "unknown"
        payload_type = "none"
        summary = "Conexión ML OK"

        try:
            if hasattr(provider, "get_listing_types"):
                operation = "get_listing_types"
                response = provider.get_listing_types()
            elif hasattr(provider, "sync"):
                operation = "sync:get_listing_types"
                response = provider.sync({"operation": "get_listing_types", "payload": {}})
            else:
                raise UserError("El provider ML no implementa métodos de diagnóstico (get_listing_types/sync).")

            payload_type = type(response).__name__

            if isinstance(response, str):
                low = response.lower()
                if "<html" in low and "access denied" in low:
                    raise UserError(
                        "Diagnóstico ML: Access Denied detectado.\n"
                        "Posible token inválido/expirado o autorización de app/callback incorrecta."
                    )
            elif isinstance(response, dict):
                raw_text = json.dumps(response, ensure_ascii=False).lower()
                if "access denied" in raw_text or "unauthorized" in raw_text or "forbidden" in raw_text:
                    raise UserError(
                        "Diagnóstico ML: respuesta no autorizada detectada (401/403/Access Denied).\n"
                        "Reautorizá la cuenta ML y verificá callback/client_id/client_secret en esta rama."
                    )

                items = response.get("items")
                if isinstance(items, list):
                    summary = f"Conexión ML OK. Listing types recibidos: {len(items)}"
                else:
                    summary = "Conexión ML respondió, pero sin lista de tipos esperada."
            else:
                summary = f"Conexión ML respondió con tipo no esperado: {payload_type}"

            _logger.info(
                "Diagnóstico ML OK product_id=%s account_id=%s op=%s payload_type=%s summary=%s",
                self.id,
                account.id,
                operation,
                payload_type,
                summary,
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Diagnóstico conexión ML",
                    "message": (
                        f"{summary}\n"
                        f"Cuenta: {account.display_name} (id={account.id})\n"
                        f"Operación: {operation}\n"
                        f"Tipo respuesta: {payload_type}"
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }

        except UserError:
            raise
        except Exception as e:
            _logger.exception(
                "Diagnóstico ML error product_id=%s account_id=%s op=%s",
                self.id,
                account.id if account else False,
                operation,
            )
            raise UserError(
                "Diagnóstico ML falló.\n"
                f"Cuenta: {account.display_name} (id={account.id})\n"
                f"Operación: {operation}\n"
                f"Detalle: {str(e)}"
            )

    def action_view_ml(self):
        self.ensure_one()
        if not self.ml_permalink:
            raise UserError("Este producto no tiene URL de publicación.")
        return {
            "type": "ir.actions.act_url",
            "url": self.ml_permalink,
            "target": "new",
        }