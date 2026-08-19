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

    # IDs de atributos de categoría que ML trata como condiciones de venta (sale_terms)
    SALE_TERM_ATTRIBUTE_IDS = {
        "WARRANTY_TYPE",
        "WARRANTY_TIME",
        "MANUFACTURING_TIME",
        "MANUFACTURING_TYPE",
        "RETURN_TYPE",
    }

    # ML no siempre expone estas condiciones vía /categories/{id}/attributes; se muestran siempre
    # (con opciones reales si la API las trae para la categoría, o como texto libre si no)
    SALE_TERM_FALLBACK_CATALOG = [
        {"id": "WARRANTY_TYPE", "name": "Tipo de garantía", "values": []},
        {"id": "WARRANTY_TIME", "name": "Tiempo de garantía", "values": []},
        {"id": "MANUFACTURING_TIME", "name": "Tiempo de fabricación (días)", "values": []},
    ]

    step = fields.Selection(
        [
            ("base", "Base"),
            ("pricing_stock", "Precio y Stock"),
            ("sale_format", "Formato de venta"),
            ("delivery", "Entrega"),
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
    publication_id = fields.Many2one(
        "marketplace.publication", string="Publicación", required=True, readonly=True, ondelete="cascade"
    )
    ml_item_id = fields.Char(related="publication_id.external_id", string="ID publicación ML")
    is_editing = fields.Boolean(string="Editando publicación existente", compute="_compute_is_editing")

    @api.depends("ml_item_id")
    def _compute_is_editing(self):
        for wizard in self:
            wizard.is_editing = bool(wizard.ml_item_id)

    ml_category_ref_id = fields.Many2one("ml.category", string="Categoría ML")
    ml_title = fields.Char(string="Título ML")
    ml_brand = fields.Char(string="Marca")
    ml_model = fields.Char(string="Modelo")
    ml_family_name_id = fields.Char(
        string="Familia/Línea de Producto", help="Atributo requerido por MercadoLibre. Ej: Porcelanato, Cerámica, etc."
    )
    listing_type_id = fields.Many2one("ml.listing.type", string="Tipo de publicación")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
    )

    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    ml_price_uom_id = fields.Many2one("uom.uom", string="UoM de precio")
    ml_use_pricelist_price = fields.Boolean(string="Usar precio desde lista", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_price = fields.Float(string="Precio ML")
    ml_stock_reserve_qty = fields.Float(string="Stock reservado", default=0.0)
    ml_effective_qty = fields.Integer(string="Stock efectivo", readonly=True)
    ml_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Forma de entrega",
        default="me2",
    )

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
    sale_term_line_ids = fields.One2many(
        "ml.publish.assistant.saleterm.line", "wizard_id", string="Condiciones de venta"
    )
    ml_warranty = fields.Char(string="Garantía")
    ml_description_html = fields.Html(string="Descripción")
    ml_required_attributes_json = fields.Text(string="Atributos requeridos", readonly=True)
    ml_recommended_attributes_json = fields.Text(string="Atributos secundarios", readonly=True)
    attribute_line_ids = fields.One2many(
        "ml.publish.assistant.attribute.line", "wizard_id", string="Atributos a publicar"
    )
    selected_attribute_line_id = fields.Many2one(
        "ml.publish.assistant.attribute.line",
        string="Línea para selector rápido",
        domain="[('wizard_id', '=', id)]",
    )

    picture_line_ids = fields.One2many(
        "ml.publish.assistant.picture.line", "wizard_id", string="Imágenes adicionales"
    )
    ml_variant_notes = fields.Text(string="Variantes/Fotos")
    validation_summary = fields.Text(string="Checklist", readonly=True)
    progress_indicator = fields.Char(string="Progreso", readonly=True, compute="_compute_progress_indicator")

    @api.depends("step")
    def _compute_progress_indicator(self):
        step_order = [
            ("base", "Base"),
            ("pricing_stock", "Precio y Stock"),
            ("sale_format", "Formato de venta"),
            ("delivery", "Entrega"),
            ("attributes", "Atributos"),
            ("variants_photos", "Variantes y fotos"),
            ("review", "Revisión final"),
        ]
        for wizard in self:
            current_idx = next(
                (i for i, (k, _) in enumerate(step_order, 1) if k == wizard.step),
                1
            )
            wizard.progress_indicator = f"Paso {current_idx} de {len(step_order)}"

    def _get_step_status(self):
        """Retorna dict con estado de cada paso: {'base': True, 'pricing_stock': True, ...}"""
        self.ensure_one()
        status = {
            "base": bool(self.ml_category_ref_id and self.listing_type_id),
            "pricing_stock": bool(self.ml_price > 0 and self.ml_effective_qty >= 0),
            "sale_format": True,  # No bloqueante
            "delivery": bool(self.ml_shipping_mode),
            "attributes": True,  # Validado en review
            "variants_photos": bool(self.picture_line_ids),
            "review": False,  # Calculado dinámicamente
        }
        return status

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

    def _compute_suggested_price(self, product, pricelist, price_uom=False):
        if not product:
            return 0.0
        if pricelist:
            try:
                return float(pricelist._get_product_price(product, 1.0, uom=price_uom or product.uom_id) or 0.0)
            except Exception:
                pass
        try:
            return float(product.uom_id._compute_price(product.list_price, price_uom or product.uom_id) or 0.0)
        except Exception:
            return float(product.ml_price or product.list_price or 0.0)

    def _compute_effective_qty(self, product, reserve_qty):
        reserve = max(0.0, reserve_qty or 0.0)
        qty_source = product.qty_available if product else 0.0
        return int(max(0.0, qty_source - reserve))

    @staticmethod
    def _parse_provider_data(raw_data):
        try:
            parsed = json.loads(raw_data or "{}")
        except (TypeError, ValueError):
            parsed = {}
        return parsed if isinstance(parsed, dict) else {}

    def _get_or_create_publication(self, product, account):
        publication = self.env["marketplace.publication"].search(
            [("product_tmpl_id", "=", product.id), ("account_id", "=", account.id)], limit=1
        )
        if publication:
            return publication

        return self.env["marketplace.publication"].create(
            {
                "product_tmpl_id": product.id,
                "account_id": account.id,
                "external_id": product.ml_item_id or False,
                "external_url": product.ml_permalink or False,
                "external_status": product.ml_status or False,
                "title": product.ml_title or product.name or "",
                "category_ref": product.ml_category_id or "",
                "listing_type": product.ml_listing_type or "gold_special",
                "condition": product.ml_condition or "new",
                "shipping_mode": product.ml_shipping_mode or "me2",
                "price": product.ml_price or 0.0,
                "price_uom_id": product.ml_price_uom_id.id or product.uom_id.id,
                "pricelist_id": product.ml_pricelist_id.id,
                "use_pricelist_price": product.ml_use_pricelist_price,
                "manual_price_override": product.ml_manual_price_override,
                "stock_reserve_qty": product.ml_stock_reserve_qty,
                "attributes_json": product.ml_attributes_json or "[]",
                "pictures_json": product.ml_pictures_json or "[]",
                "sale_terms_json": product.ml_sale_terms_json or "[]",
                "provider_data_json": json.dumps(
                    {
                        "brand": product.ml_brand or "",
                        "model": product.ml_model or "",
                        "family_name": product.ml_family_name_id or "",
                        "warranty": product.ml_warranty or "",
                        "description_html": product.ml_description_html or "",
                    },
                    ensure_ascii=False,
                ),
            }
        )

    @api.onchange("ml_category_ref_id")
    def _onchange_category_ref(self):
        """Auto-load metadata cuando se selecciona categoría"""
        for wizard in self:
            if wizard.ml_category_ref_id and wizard.step == "base":
                # No ejecutamos directamente aquí; el usuario debe hacer clic
                # para cargar, pero podemos dejar preparado el mensaje
                pass

    @api.onchange("ml_pricelist_id", "ml_price_uom_id", "ml_use_pricelist_price", "ml_manual_price_override", "ml_stock_reserve_qty")
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
                wizard.ml_price = wizard._compute_suggested_price(product, wizard.ml_pricelist_id, wizard.ml_price_uom_id)
            else:
                wizard.ml_price = product.ml_price or product.list_price

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        # Forzar que siempre comience en el paso "base"
        vals["step"] = "base"
        if "name" in fields_list and not vals.get("name"):
            vals["name"] = "Asistente publicación ML"
        if "status" in fields_list and "status" not in vals:
            vals["status"] = ""
        publication = self.env["marketplace.publication"].browse(
            self.env.context.get("default_publication_id")
        ).exists()
        product_id = publication.product_tmpl_id.id if publication else self.env.context.get("default_product_tmpl_id")
        if not product_id:
            return vals
        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            return vals

        account = publication.account_id if publication else product.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay cuenta SCE MercadoLibre activa configurada.")

        if not publication:
            publication = self._get_or_create_publication(product, account)
        provider_data = self._parse_provider_data(publication.provider_data_json)

        self.env["ml.category"].refresh_for_account(account, query=publication.title or product.name or "")
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
            [("account_id", "=", account.id), ("listing_type_id", "=", (publication.listing_type or "").strip())],
            limit=1,
        )

        suggested_price = self._compute_suggested_price(
            product,
            publication.pricelist_id if publication.use_pricelist_price else False,
            publication.price_uom_id,
        )
        effective_qty = self._compute_effective_qty(product, publication.stock_reserve_qty)

        selected_category = self.env["ml.category"].search(
            [("account_id", "=", account.id), ("category_id", "=", (publication.category_ref or "").strip())],
            limit=1,
        )

        vals.update(
            {
                "product_tmpl_id": product.id,
                "account_id": account.id,
                "publication_id": publication.id,
                "ml_category_ref_id": selected_category.id if selected_category else False,
                "ml_title": publication.title or product.name or "",
                "listing_type_id": selected_listing.id if selected_listing else False,
                "ml_brand": provider_data.get("brand") or "",
                "ml_model": provider_data.get("model") or "",
                "ml_family_name_id": provider_data.get("family_name") or "",
                "ml_condition": publication.condition or "new",
                "ml_pricelist_id": publication.pricelist_id.id,
                "ml_price_uom_id": publication.price_uom_id.id or product.uom_id.id,
                "ml_use_pricelist_price": publication.use_pricelist_price,
                "ml_manual_price_override": publication.manual_price_override,
                "ml_price": publication.price if publication.manual_price_override else suggested_price,
                "ml_stock_reserve_qty": publication.stock_reserve_qty,
                "ml_effective_qty": effective_qty,
                "ml_shipping_mode": publication.shipping_mode or "me2",
                "ml_sales_unit_value_id": False,
                "ml_yield_value": 0.0,
                "ml_yield_unit": "m2",
                "ml_warranty": provider_data.get("warranty") or "",
                "ml_description_html": provider_data.get("description_html") or "",
                "ml_variant_notes": "",
            }
        )

        picture_commands = []
        seq = 10
        seen = set()
        try:
            publication_pictures = json.loads(publication.pictures_json or "[]")
        except (TypeError, ValueError):
            publication_pictures = []
        picture_items = publication_pictures if isinstance(publication_pictures, list) else []
        if not picture_items:
            picture_items = product._collect_ml_pictures(account=account)
        for item in picture_items:
            if not isinstance(item, dict):
                continue
            source = (item.get("source") or "").strip()
            if not source or source in seen:
                continue
            seen.add(source)
            picture_commands.append((0, 0, {"sequence": seq, "source": source}))
            seq += 10

        if picture_commands:
            vals["picture_line_ids"] = picture_commands

        return vals

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_list = []
        allowed_fields = set(self._fields.keys())
        for vals in vals_list:
            safe_vals = dict(vals or {})
            safe_vals["step"] = "base"
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
        if self.is_editing:
            raise UserError("La categoría no se puede modificar una vez publicado el producto en MercadoLibre.")
        self.action_apply_to_product()
        product = self.product_tmpl_id
        wizard = self.env["ml.category.search.wizard"].create(
            {
                "product_tmpl_id": product.id,
                "account_id": self.account_id.id,
                "publication_id": self.publication_id.id,
                "query": self.ml_title or product.name or "",
                "selected_category_id": (
                    self.ml_category_ref_id.category_id if self.ml_category_ref_id else (self.publication_id.category_ref or "")
                ),
                "publish_wizard_id": self.id,
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

    def _open_attribute_picker_for_line(self, line):
        self.ensure_one()
        if not line or line.wizard_id.id != self.id:
            raise UserError("No se encontró la línea de atributo para seleccionar opción.")
        if not self.ml_category_ref_id:
            raise UserError("Primero define categoría ML en el Paso 1.")
        wizard = self.env["ml.attribute.option.picker.wizard"].create(
            {
                "wizard_id": self.id,
                "line_id": line.id,
                "account_id": self.account_id.id,
                "category_id": self.ml_category_ref_id.category_id or "",
                "attribute_id": line.attribute_id or "",
                "attribute_name": line.attribute_name or "",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.attribute.option.picker.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def action_open_attribute_option_picker(self):
        self.ensure_one()
        line_id = self.env.context.get("line_id")
        line = self.env["ml.publish.assistant.attribute.line"].browse(line_id).exists()
        return self._open_attribute_picker_for_line(line)

    def action_open_attribute_option_picker_from_selected(self):
        self.ensure_one()
        line = self.selected_attribute_line_id
        if not line:
            raise UserError("Selecciona una línea de atributo antes de abrir el selector.")
        return self._open_attribute_picker_for_line(line)

    def action_next(self):
        self.ensure_one()
        order = ["base", "pricing_stock", "sale_format", "delivery", "attributes", "variants_photos", "review"]
        current_step = self.step if self.step in order else "base"
        if not self.step:
            self.step = current_step
        
        # Guardamos cambios antes de pasar al siguiente paso
        self.action_apply_to_product()
        
        idx = order.index(current_step)
        if idx < len(order) - 1:
            next_step = order[idx + 1]
            # Auto-trigger metadata load al llegar a attributes
            if next_step == "attributes" and self.ml_category_ref_id and not self.attribute_line_ids:
                self.step = next_step
                self.action_load_ml_metadata()
                return
            self.step = next_step
        return self._reload_self()

    def action_prev(self):
        self.ensure_one()
        # Guardar cambios antes de retroceder
        self.action_apply_to_product()
        
        order = ["base", "pricing_stock", "sale_format", "delivery", "attributes", "variants_photos", "review"]
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
                    "category_id": category_id,
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
                                ("category_id", "=", category_id),
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
        self.sale_term_line_ids.unlink()

        combined = [a for a in (required + recommended) if isinstance(a, dict) and (a.get("id") or "").strip()]
        combined_map = {(a.get("id") or "").strip(): a for a in combined}
        regular_attrs = [a for a in combined if (a.get("id") or "").strip() not in self.SALE_TERM_ATTRIBUTE_IDS]

        # ML no siempre expone WARRANTY_TYPE/MANUFACTURING_TIME/etc. como atributo de categoría:
        # usamos lo que la API haya devuelto y completamos con un catálogo fijo para que el paso nunca quede vacío.
        sale_term_attrs = []
        for fallback in self.SALE_TERM_FALLBACK_CATALOG:
            tid = fallback["id"]
            sale_term_attrs.append(combined_map.get(tid) or fallback)

        commands = []
        seq = 10
        for attr in regular_attrs:
            aid = (attr.get("id") or "").strip()
            values = attr.get("values") if isinstance(attr.get("values"), list) else []
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": seq,
                        "attribute_id": aid,
                        "attribute_name": (attr.get("name") or aid).strip(),
                        "required": aid in req_ids,
                        "has_options": bool(values),
                        "value_id": "",
                        "value_name": "",
                    },
                )
            )
            seq += 10
        if commands:
            self.write({"attribute_line_ids": commands})

        saleterm_commands = []
        seq = 10
        for attr in sale_term_attrs:
            aid = (attr.get("id") or "").strip()
            values = attr.get("values") if isinstance(attr.get("values"), list) else []
            saleterm_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": seq,
                        "term_id": aid,
                        "term_name": (attr.get("name") or aid).strip(),
                        "required": aid in req_ids,
                        "has_options": bool(values),
                        "value_id": "",
                        "value_name": "",
                    },
                )
            )
            seq += 10
        if saleterm_commands:
            self.write({"sale_term_line_ids": saleterm_commands})

        option_model = self.env["ml.attribute.option"]
        for attr in combined:
            aid = (attr.get("id") or "").strip()
            if not aid:
                continue
            values = attr.get("values") if isinstance(attr.get("values"), list) else []
            for opt in values:
                if not isinstance(opt, dict):
                    continue
                value_id = (opt.get("id") or "").strip()
                value_name = (opt.get("name") or value_id).strip()
                if not value_id and not value_name:
                    continue
                existing = option_model.search(
                    [
                        ("account_id", "=", self.account_id.id),
                        ("category_id", "=", category_id),
                        ("attribute_id", "=", aid),
                        ("value_id", "=", value_id),
                    ],
                    limit=1,
                )
                vals_opt = {
                    "account_id": self.account_id.id,
                    "category_id": category_id,
                    "attribute_id": aid,
                    "attribute_name": (attr.get("name") or aid).strip(),
                    "value_id": value_id,
                    "value_name": value_name,
                }
                if existing:
                    existing.write({"value_name": vals_opt["value_name"], "attribute_name": vals_opt["attribute_name"]})
                else:
                    option_model.create(vals_opt)

        self.ml_required_attributes_json = json.dumps(
            [a for a in required if (a.get("id") or "").strip() not in self.SALE_TERM_ATTRIBUTE_IDS],
            ensure_ascii=False,
            indent=2,
        )
        self.ml_recommended_attributes_json = json.dumps(recommended, ensure_ascii=False, indent=2)
        return self._reload_self()

    def action_apply_to_product(self):
        self.ensure_one()
        product = self.product_tmpl_id
        publication = self.publication_id

        sale_terms_payload = []
        for line in self.sale_term_line_ids.sorted("sequence"):
            tid = (line.term_id or "").strip()
            if not tid:
                continue
            item = {"id": tid}
            opt = line.term_option_id
            effective_value_id = (opt.value_id or "").strip() if opt else (line.value_id or "").strip()
            effective_value_name = (opt.value_name or "").strip() if opt else (line.value_name or "").strip()
            if effective_value_id:
                item["value_id"] = effective_value_id
            if effective_value_name:
                item["value_name"] = effective_value_name
            if item.get("value_id") or item.get("value_name"):
                sale_terms_payload.append(item)

        attrs_payload = []
        for line in self.attribute_line_ids.sorted("sequence"):
            aid = (line.attribute_id or "").strip()
            if not aid:
                continue
            item = {"id": aid}
            opt = getattr(line, "attribute_option_id", False)
            effective_value_id = (opt.value_id or "").strip() if opt else (line.value_id or "").strip()
            effective_value_name = (opt.value_name or "").strip() if opt else (line.value_name or "").strip()
            if effective_value_id:
                item["value_id"] = effective_value_id
            if effective_value_name:
                item["value_name"] = effective_value_name
            if item.get("value_id") or item.get("value_name"):
                attrs_payload.append(item)

            unit_labels = {"m2": "m²", "m": "m", "cm2": "cm²", "un": "Unidad"}
            yield_unit = unit_labels.get(self.ml_yield_unit, self.ml_yield_unit or "m²")
            for item in attrs_payload:
                if item.get("id") != "YIELD_OF_SALES_UNIT":
                    continue
                raw_value = (item.get("value_name") or "").strip()
                try:
                    yield_value = self.ml_yield_value if self.ml_yield_value > 0 else float(raw_value)
                except (TypeError, ValueError):
                    continue
                item.pop("value_id", None)
                item["value_name"] = f"{yield_value:.2f} {yield_unit}"

            attribute_ids = {(item.get("id") or "").strip() for item in attrs_payload}
            if self.ml_sales_unit_value_id and "SALES_UNIT" not in attribute_ids:
                attrs_payload.append({"id": "SALES_UNIT", "value_id": self.ml_sales_unit_value_id.value_id})
            if self.ml_yield_value > 0 and "YIELD_OF_SALES_UNIT" not in attribute_ids:
                attrs_payload.append(
                    {"id": "YIELD_OF_SALES_UNIT", "value_name": f"{self.ml_yield_value:.2f} {yield_unit}"}
                )

        pictures_payload = []
        seen_sources = set()
        for line in self.picture_line_ids.sorted("sequence"):
            source = (line.source or "").strip()
            if not product._is_valid_ml_picture_source(source):
                continue
            if source in seen_sources:
                continue
            seen_sources.add(source)
            pictures_payload.append({"source": source})

        state_by_step = {
            "base": "category",
            "pricing_stock": "pricing",
            "sale_format": "attributes",
            "delivery": "shipping",
            "attributes": "attributes",
            "variants_photos": "pictures",
            "review": "ready",
        }
        publication.write(
            {
                "title": (self.ml_title or product.name or "").strip(),
                "category_ref": (self.ml_category_ref_id.category_id if self.ml_category_ref_id else "").strip(),
                "category_name": self.ml_category_ref_id.category_name if self.ml_category_ref_id else "",
                "listing_type": self.listing_type_id.listing_type_id if self.listing_type_id else "gold_special",
                "condition": self.ml_condition or "new",
                "pricelist_id": self.ml_pricelist_id.id if self.ml_pricelist_id else False,
                "price_uom_id": self.ml_price_uom_id.id if self.ml_price_uom_id else product.uom_id.id,
                "use_pricelist_price": bool(self.ml_use_pricelist_price),
                "manual_price_override": bool(self.ml_manual_price_override),
                "price": self.ml_price or 0.0,
                "stock_reserve_qty": max(0.0, self.ml_stock_reserve_qty or 0.0),
                "shipping_mode": self.ml_shipping_mode or "me2",
                "sale_terms_json": json.dumps(sale_terms_payload, ensure_ascii=False),
                "attributes_json": json.dumps(attrs_payload, ensure_ascii=False),
                "pictures_json": json.dumps(pictures_payload, ensure_ascii=False),
                "provider_data_json": json.dumps(
                    {
                        "brand": (self.ml_brand or "").strip(),
                        "model": (self.ml_model or "").strip(),
                        "family_name": (self.ml_family_name_id or "").strip(),
                        "warranty": (self.ml_warranty or "").strip(),
                        "description_html": self.ml_description_html or "",
                    },
                    ensure_ascii=False,
                ),
                "state": state_by_step.get(self.step, "draft"),
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
                if not product._is_valid_ml_picture_source(src):
                    image_errors.append("Hay imágenes inválidas para ML.")
                    break

        attribute_errors = []
        warnings_by_attr = []
        required_map = {}
        try:
            required_raw = json.loads(self.ml_required_attributes_json or "[]")
            if isinstance(required_raw, list):
                for a in required_raw:
                    if isinstance(a, dict):
                        rid = (a.get("id") or "").strip()
                        if rid:
                            required_map[rid] = (a.get("name") or rid).strip()
        except Exception:
            required_map = {}

        required_lines = self.attribute_line_ids.filtered(lambda l: l.required)
        for line in required_lines:
            opt = getattr(line, "attribute_option_id", False)
            effective_value_id = (opt.value_id or "").strip() if opt else (line.value_id or "").strip()
            effective_value_name = (opt.value_name or "").strip() if opt else (line.value_name or "").strip()
            has_value = bool(effective_value_id or effective_value_name)
            if not has_value:
                pretty = required_map.get((line.attribute_id or "").strip(), line.attribute_name or line.attribute_id)
                attribute_errors.append(f"Falta atributo requerido ML: {pretty}")

        for line in self.attribute_line_ids:
            aid = (line.attribute_id or "").strip()
            if not aid:
                continue
            if getattr(line, "attribute_option_id", False):
                continue
            has_manual = bool((line.value_id or "").strip() or (line.value_name or "").strip())
            if has_manual:
                continue
            opt_count = self.env["ml.attribute.option"].search_count(
                [
                    ("account_id", "=", self.account_id.id),
                    ("category_id", "=", self.ml_category_ref_id.category_id if self.ml_category_ref_id else ""),
                    ("attribute_id", "=", aid),
                ]
            )
            if opt_count:
                warnings_by_attr.append(
                    f"Atributo '{line.attribute_name or aid}' tiene opciones sugeridas. Elegí una en la columna 'Opción sugerida'."
                )

        sale_terms_errors = []
        required_saleterm_lines = self.sale_term_line_ids.filtered(lambda l: l.required)
        for line in required_saleterm_lines:
            opt = line.term_option_id
            effective_value_id = (opt.value_id or "").strip() if opt else (line.value_id or "").strip()
            effective_value_name = (opt.value_name or "").strip() if opt else (line.value_name or "").strip()
            if not (effective_value_id or effective_value_name):
                sale_terms_errors.append(f"Falta condición de venta requerida ML: {line.term_name or line.term_id}")

        if not (self.ml_brand or "").strip():
            warnings.append("Recomendado: completar Marca.")
        if not (self.ml_model or "").strip():
            warnings.append("Recomendado: completar Modelo.")
        if not self.ml_family_name_id:
            warnings.append("Importante: MercadoLibre requiere 'Familia/Línea' para muchas categorías. Completa este campo en Paso 1 para evitar errores de publicación.")
        if not self.sale_term_line_ids:
            warnings.append("Recomendado: cargá los atributos de la categoría en el Paso 1 para ver sus condiciones de venta.")
        warnings.extend(warnings_by_attr)

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
            lines.append("Estado: necesita corrección")
            lines.extend(errors)
        else:
            lines.append("Estado: listo para publicar")

        if warnings:
            lines.append("")
            lines.append("Recomendaciones:")
            lines.extend([f"- {w}" for w in warnings])

        self.validation_summary = "\n".join(lines)
        return self._reload_self()

    def action_publish(self):
        self.ensure_one()
        self.action_validate_checklist()
        if "CON OBSERVACIONES BLOQUEANTES" in (self.validation_summary or ""):
            raise UserError(
                "No se puede publicar hasta resolver los bloqueantes del checklist.\n"
                "Revisá Paso 4 (Atributos) y Paso 6 (Revisión final)."
            )
        try:
            self.action_apply_to_product()
            self.env["marketplace.publication.service"].publish(self.publication_id)
        except UserError:
            self.publication_id.write({"state": "failed", "error_message": "Error al publicar en MercadoLibre."})
            raise
        except Exception:
            _logger.exception(
                "Error publicando en ML para product_tmpl_id=%s account_id=%s",
                self.product_tmpl_id.id if self.product_tmpl_id else False,
                self.account_id.id if self.account_id else False,
            )
            self.publication_id.write({"state": "failed", "error_message": "Error inesperado al publicar en MercadoLibre."})
            raise UserError(
                "No se pudo publicar en MercadoLibre. "
                "Verifica credenciales/permisos de la cuenta y revisa los logs del servidor."
            )
        return {"type": "ir.actions.act_window_close"}


class MlPublishAssistantPictureLine(models.TransientModel):
    _name = "ml.publish.assistant.picture.line"
    _description = "Línea de imágenes del asistente ML"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    source = fields.Char(required=True)