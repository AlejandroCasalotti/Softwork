# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

_logger = logging.getLogger(__name__)


class MlPublishAssistantWizard(models.TransientModel):
    _name = "ml.publish.assistant.wizard"
    _description = "Asistente único de publicación MercadoLibre"

    step = fields.Selection(
        [
            ("base", "Base"),
            ("pricing_stock", "Precio y Stock"),
            ("sale_format", "Formato de venta"),
            ("attributes", "Atributos"),
            ("variants_photos", "Variantes y fotos"),
            ("review", "Revisión final"),
        ],
        default="base",
    )

    name = fields.Char(string="Nombre", default="Asistente publicación ML")
    status = fields.Char(string="Estado")
    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    account_id = fields.Many2one("sce.account", string="Cuenta ML", required=True, readonly=True)

    ml_category_ref_id = fields.Many2one("ml.category", string="Categoría ML")
    ml_brand = fields.Char(string="Marca")
    ml_model = fields.Char(string="Modelo")
    listing_type_id = fields.Many2one("ml.listing.type", string="Tipo de publicación")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
    )

    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    ml_use_pricelist_price = fields.Boolean(string="Usar precio desde lista", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_price = fields.Float(string="Precio ML")
    ml_stock_reserve_qty = fields.Float(string="Stock reservado", default=0.0)
    ml_effective_qty = fields.Integer(string="Stock efectivo", readonly=True)

    ml_sales_unit_value_id = fields.Many2one("ml.attribute.option", string="Unidad de venta")
    ml_yield_value = fields.Float(string="Rendimiento")
    ml_yield_unit = fields.Selection(
        [
            ("m2", "m²"),
            ("m", "m"),
            ("cm2", "cm²"),
            ("un", "Unidad"),
        ],
        string="Unidad de rendimiento",
        default="m2",
    )
    ml_sale_terms_json = fields.Text(string="Formato de venta (sale_terms JSON)")
    ml_required_attributes_json = fields.Text(string="Atributos requeridos", readonly=True)
    ml_recommended_attributes_json = fields.Text(string="Atributos secundarios", readonly=True)
    attribute_line_ids = fields.One2many(
        "ml.publish.assistant.attribute.line", "wizard_id", string="Atributos a publicar"
    )

    picture_line_ids = fields.One2many(
        "ml.publish.assistant.picture.line", "wizard_id", string="Imágenes adicionales"
    )
    ml_variant_notes = fields.Text(string="Variantes/Fotos")
    validation_summary = fields.Text(string="Checklist", readonly=True)

    def _raise_if_access_denied_response(self, payload, operation):
        if isinstance(payload, str):
            text = payload.lower()
            if "<html" in text and "access denied" in text:
                safe_account = self.account_id or self.product_tmpl_id.ml_account_id
                _logger.error(
                    "Access Denied detectado en operación ML '%s' para account_id=%s",
                    operation,
                    safe_account.id if safe_account else False,
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

    def _compute_effective_qty(self, product, reserve_qty):
        reserve = max(0.0, reserve_qty or 0.0)
        qty_source = product.qty_available if product else 0.0
        return int(max(0.0, qty_source - reserve))

    @api.onchange("ml_pricelist_id", "ml_use_pricelist_price", "ml_manual_price_override", "ml_stock_reserve_qty")
    def _onchange_pricing_stock(self):
        for wizard in self:
            product = wizard.product_tmpl_id
            if not product:
                continue

            wizard.ml_effective_qty = wizard._compute_effective_qty(product, wizard.ml_stock_reserve_qty)

            if wizard.ml_manual_price_override:
                if not wizard.ml_price:
                    wizard.ml_price = product.ml_price or product.list_price
            elif wizard.ml_use_pricelist_price:
                wizard.ml_price = wizard._compute_suggested_price(product, wizard.ml_pricelist_id)
            else:
                wizard.ml_price = product.ml_price or product.list_price

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if "name" in fields_list and not vals.get("name"):
            vals["name"] = "Asistente publicación ML"
        if "status" in fields_list and "status" not in vals:
            vals["status"] = ""
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

        self.env["ml.category"].refresh_for_account(account, query=product.ml_title or product.name or "")
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
        seen_listing_ids = set()

        for item in listing_items:
            if not isinstance(item, dict):
                continue
            ltid = (item.get("id") or "").strip()
            if not ltid:
                continue
            seen_listing_ids.add(ltid)
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

        suggested_price = self._compute_suggested_price(product, product.ml_pricelist_id if product.ml_use_pricelist_price else False)
        effective_qty = self._compute_effective_qty(product, product.ml_stock_reserve_qty)

        selected_category = self.env["ml.category"].search(
            [("account_id", "=", account.id), ("category_id", "=", (product.ml_category_id or "").strip())],
            limit=1,
        )

        vals.update(
            {
                "product_tmpl_id": product.id,
                "account_id": account.id,
                "ml_category_ref_id": selected_category.id if selected_category else False,
                "listing_type_id": selected_listing.id if selected_listing else False,
                "ml_brand": product.ml_brand or "",
                "ml_model": product.ml_model or "",
                "ml_condition": product.ml_condition or "new",
                "ml_pricelist_id": product.ml_pricelist_id.id if product.ml_pricelist_id else False,
                "ml_use_pricelist_price": product.ml_use_pricelist_price,
                "ml_manual_price_override": product.ml_manual_price_override,
                "ml_price": product.ml_price if product.ml_manual_price_override else suggested_price,
                "ml_stock_reserve_qty": product.ml_stock_reserve_qty,
                "ml_effective_qty": effective_qty,
                "ml_sales_unit_value_id": False,
                "ml_yield_value": 0.0,
                "ml_yield_unit": "m2",
                "ml_sale_terms_json": product.ml_sale_terms_json or "[]",
                "ml_variant_notes": "",
            }
        )

        picture_commands = []
        raw_pictures = (product.ml_pictures_json or "").strip()
        if raw_pictures:
            try:
                parsed = json.loads(raw_pictures)
                if isinstance(parsed, list):
                    seq = 10
                    seen = set()
                    for item in parsed:
                        if not isinstance(item, dict):
                            continue
                        source = (item.get("source") or "").strip()
                        if not source or source in seen:
                            continue
                        seen.add(source)
                        picture_commands.append((0, 0, {"sequence": seq, "source": source}))
                        seq += 10
            except Exception:
                picture_commands = []

        if picture_commands:
            vals["picture_line_ids"] = picture_commands

        return vals

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_list = []
        allowed_fields = set(self._fields.keys())
        for vals in vals_list:
            safe_vals = dict(vals or {})
            unknown_keys = [k for k in safe_vals.keys() if k not in allowed_fields]
            if unknown_keys:
                _logger.warning(
                    "ml.publish.assistant.wizard.create: ignorando campos desconocidos: %s",
                    ",".join(sorted(unknown_keys)),
                )
                for key in unknown_keys:
                    safe_vals.pop(key, None)
            sanitized_list.append(safe_vals)
        return super().create(sanitized_list)

    def action_open_category_search(self):
        self.ensure_one()
        product = self.product_tmpl_id
        wizard = self.env["ml.category.search.wizard"].create(
            {
                "product_tmpl_id": product.id,
                "account_id": self.account_id.id,
                "query": product.ml_title or product.name or "",
                "selected_category_id": (
                    self.ml_category_ref_id.category_id if self.ml_category_ref_id else (product.ml_category_id or "")
                ),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.category.search.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": {
                "default_product_tmpl_id": product.id,
            },
        }

    def action_next(self):
        self.ensure_one()
        order = ["base", "pricing_stock", "sale_format", "attributes", "variants_photos", "review"]
        current_step = self.step if self.step in order else "base"
        if not self.step:
            self.step = current_step
        idx = order.index(current_step)
        if idx < len(order) - 1:
            self.step = order[idx + 1]
        return self._reload_self()

    def action_prev(self):
        self.ensure_one()
        order = ["base", "pricing_stock", "sale_format", "attributes", "variants_photos", "review"]
        current_step = self.step if self.step in order else "base"
        if not self.step:
            self.step = current_step
        idx = order.index(current_step)
        if idx > 0:
            self.step = order[idx - 1]
        return self._reload_self()

    def _reload_self(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.assistant.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_load_ml_metadata(self):
        self.ensure_one()
        category = self.ml_category_ref_id
        category_id = (category.category_id or "").strip() if category else ""
        if not category_id:
            raise UserError("Define categoría ML para cargar metadatos.")

        self.env["ml.category"].refresh_for_account(self.account_id, query="")
        provider = ProviderFactory.get_provider(self.account_id)
        req_res = provider.get_category_required_fields(category_id=category_id)
        self._raise_if_access_denied_response(req_res, "get_category_required_fields")
        required = req_res.get("items") if isinstance(req_res, dict) else []
        if not isinstance(required, list):
            _logger.warning(
                "Respuesta inesperada en get_category_required_fields account_id=%s category_id=%s: %s",
                self.account_id.id,
                category_id,
                type(req_res).__name__,
            )
            required = []

        attrs_res = provider.get_category_attributes(category_id=category_id)
        self._raise_if_access_denied_response(attrs_res, "get_category_attributes")
        attrs = attrs_res.get("items") if isinstance(attrs_res, dict) else []
        if not isinstance(attrs, list):
            _logger.warning(
                "Respuesta inesperada en get_category_attributes account_id=%s category_id=%s: %s",
                self.account_id.id,
                category_id,
                type(attrs_res).__name__,
            )
            attrs = []

        req_ids = {(a.get("id") or "").strip() for a in required if isinstance(a, dict)}
        req_ids.discard("")
        recommended = []
        for a in attrs:
            if not isinstance(a, dict):
                continue
            aid = (a.get("id") or "").strip()
            if aid and aid not in req_ids:
                recommended.append(a)

        sales_unit_options = []
        for a in required:
            if isinstance(a, dict) and (a.get("id") or "").strip() == "SALES_UNIT":
                sales_unit_options = a.get("values") if isinstance(a.get("values"), list) else []
                break

        if sales_unit_options:
            option_model = self.env["ml.attribute.option"]
            existing_opts = option_model.search(
                [("account_id", "=", self.account_id.id), ("attribute_id", "=", "SALES_UNIT")]
            )
            existing_map = {rec.value_id: rec for rec in existing_opts if rec.value_id}
            seen_value_ids = set()
            for opt in sales_unit_options:
                if not isinstance(opt, dict):
                    continue
                value_id = (opt.get("id") or "").strip()
                value_name = (opt.get("name") or "").strip()
                if not value_id:
                    continue
                seen_value_ids.add(value_id)
                vals = {
                    "account_id": self.account_id.id,
                    "attribute_id": "SALES_UNIT",
                    "attribute_name": "Unidad de venta",
                    "value_id": value_id,
                    "value_name": value_name or value_id,
                }
                existing = existing_map.get(value_id)
                if existing:
                    existing.write({"value_name": vals["value_name"], "attribute_name": vals["attribute_name"]})
                else:
                    try:
                        option_model.create(vals)
                    except Exception:
                        _logger.warning(
                            "Posible concurrencia/duplicado creando SALES_UNIT option account_id=%s value_id=%s",
                            self.account_id.id,
                            value_id,
                        )
                        retry = option_model.search(
                            [
                                ("account_id", "=", self.account_id.id),
                                ("attribute_id", "=", "SALES_UNIT"),
                                ("value_id", "=", value_id),
                            ],
                            limit=1,
                        )
                        if retry:
                            retry.write({"value_name": vals["value_name"], "attribute_name": vals["attribute_name"]})
                        else:
                            raise
            stale_opts = existing_opts.filtered(lambda r: r.value_id and r.value_id not in seen_value_ids)
            if stale_opts:
                stale_opts.unlink()

        self.attribute_line_ids.unlink()
        commands = []
        seq = 10
        for attr in required + recommended:
            if not isinstance(attr, dict):
                continue
            aid = (attr.get("id") or "").strip()
            if not aid:
                continue
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": seq,
                        "attribute_id": aid,
                        "attribute_name": (attr.get("name") or aid).strip(),
                        "required": aid in req_ids,
                        "value_id": "",
                        "value_name": "",
                    },
                )
            )
            seq += 10
        if commands:
            self.write({"attribute_line_ids": commands})

        self.ml_required_attributes_json = json.dumps(required, ensure_ascii=False, indent=2)
        self.ml_recommended_attributes_json = json.dumps(recommended, ensure_ascii=False, indent=2)
        return self._reload_self()

    def action_apply_to_product(self):
        self.ensure_one()
        product = self.product_tmpl_id

        sale_terms = []
        if self.ml_sales_unit_value_id:
            sale_terms.append({"id": "SALES_UNIT", "value_id": self.ml_sales_unit_value_id.value_id})
        if self.ml_yield_value > 0:
            sale_terms.append(
                {
                    "id": "YIELD_OF_SALES_UNIT",
                    "value_name": str(self.ml_yield_value),
                    "value_struct": {"number": self.ml_yield_value, "unit": self.ml_yield_unit or "m2"},
                }
            )

        attrs_payload = []
        for line in self.attribute_line_ids.sorted("sequence"):
            aid = (line.attribute_id or "").strip()
            if not aid:
                continue
            item = {"id": aid}
            if (line.value_id or "").strip():
                item["value_id"] = line.value_id.strip()
            if (line.value_name or "").strip():
                item["value_name"] = line.value_name.strip()
            if item.get("value_id") or item.get("value_name"):
                attrs_payload.append(item)

        pictures_payload = []
        seen_sources = set()
        for line in self.picture_line_ids.sorted("sequence"):
            source = (line.source or "").strip()
            if not source:
                continue
            if not source.startswith(("http://", "https://")) or len(source) > 1024:
                continue
            if source in seen_sources:
                continue
            seen_sources.add(source)
            pictures_payload.append({"source": source})

        product.write(
            {
                "ml_category_id": (self.ml_category_ref_id.category_id if self.ml_category_ref_id else "").strip(),
                "ml_listing_type": self.listing_type_id.listing_type_id if self.listing_type_id else "gold_special",
                "ml_brand": (self.ml_brand or "").strip(),
                "ml_model": (self.ml_model or "").strip(),
                "ml_condition": self.ml_condition or "new",
                "ml_pricelist_id": self.ml_pricelist_id.id if self.ml_pricelist_id else False,
                "ml_use_pricelist_price": bool(self.ml_use_pricelist_price),
                "ml_manual_price_override": bool(self.ml_manual_price_override),
                "ml_price": self.ml_price if self.ml_manual_price_override else product.ml_price,
                "ml_stock_reserve_qty": max(0.0, self.ml_stock_reserve_qty or 0.0),
                "ml_sale_terms_json": json.dumps(sale_terms, ensure_ascii=False) if sale_terms else (self.ml_sale_terms_json or "[]"),
                "ml_attributes_json": json.dumps(attrs_payload, ensure_ascii=False),
                "ml_pictures_json": json.dumps(pictures_payload, ensure_ascii=False),
            }
        )

        return {"type": "ir.actions.act_window_close"}

    def action_validate_checklist(self):
        self.ensure_one()
        product = self.product_tmpl_id
        errors = []
        warnings = []

        base_errors = []
        if not self.ml_category_ref_id:
            base_errors.append("Falta categoría ML.")
        if not self.listing_type_id:
            base_errors.append("Falta tipo de publicación.")
        if not (self.ml_condition or "").strip():
            base_errors.append("Falta condición.")

        pricing_errors = []
        if self.ml_price <= 0:
            pricing_errors.append("Precio ML inválido.")
        if self.ml_effective_qty < 0:
            pricing_errors.append("Stock efectivo inválido.")

        image_errors = []
        wizard_pictures = [{"source": (l.source or "").strip()} for l in self.picture_line_ids if (l.source or "").strip()]
        pictures = wizard_pictures or product._collect_ml_pictures()
        if not pictures:
            image_errors.append("Faltan imágenes públicas válidas.")
        else:
            for p in pictures:
                src = (p.get("source") or "").strip()
                if not src.startswith(("http://", "https://")) or len(src) > 1024:
                    image_errors.append("Hay imágenes inválidas para ML.")
                    break

        attribute_errors = []
        attrs = product._parse_ml_attributes()
        attribute_errors.extend(product._validate_ml_required_attributes(attrs))

        sale_terms_errors = []
        raw_terms = (self.ml_sale_terms_json or "").strip()
        if raw_terms:
            try:
                parsed_terms = json.loads(raw_terms)
                if not isinstance(parsed_terms, list):
                    sale_terms_errors.append("sale_terms debe ser una lista.")
                elif any(not isinstance(t, dict) for t in parsed_terms):
                    sale_terms_errors.append("sale_terms debe contener solo objetos.")
            except Exception:
                sale_terms_errors.append("sale_terms JSON inválido.")

        if not (product.ml_brand or "").strip():
            warnings.append("Recomendado: completar Marca.")
        if not (product.ml_model or "").strip():
            warnings.append("Recomendado: completar Modelo.")
        if not raw_terms:
            warnings.append("Recomendado: definir sale_terms para mejorar calidad de publicación.")

        if base_errors:
            errors.append("[Base]")
            errors.extend([f"- {e}" for e in base_errors])
        if pricing_errors:
            errors.append("[Precio/Stock]")
            errors.extend([f"- {e}" for e in pricing_errors])
        if image_errors:
            errors.append("[Imágenes]")
            errors.extend([f"- {e}" for e in image_errors])
        if attribute_errors:
            errors.append("[Atributos]")
            errors.extend([f"- {e}" for e in attribute_errors])
        if sale_terms_errors:
            errors.append("[Formato de venta / sale_terms]")
            errors.extend([f"- {e}" for e in sale_terms_errors])

        lines = []
        if errors:
            lines.append("Estado: CON OBSERVACIONES BLOQUEANTES")
            lines.extend(errors)
        else:
            lines.append("Estado: OK (sin bloqueantes)")

        if warnings:
            lines.append("")
            lines.append("Recomendaciones:")
            lines.extend([f"- {w}" for w in warnings])

        self.validation_summary = "\n".join(lines)
        return self._reload_self()

    def action_publish(self):
        self.ensure_one()
        try:
            self.action_apply_to_product()
            self.product_tmpl_id.action_publish_ml()
        except UserError:
            raise
        except Exception:
            _logger.exception(
                "Error publicando en ML para product_tmpl_id=%s account_id=%s",
                self.product_tmpl_id.id if self.product_tmpl_id else False,
                self.account_id.id if self.account_id else False,
            )
            raise UserError(
                "No se pudo publicar en MercadoLibre. "
                "Verifica credenciales/permisos de la cuenta y revisa los logs del servidor."
            )
        return {"type": "ir.actions.act_window_close"}