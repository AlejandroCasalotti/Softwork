# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

_logger = logging.getLogger(__name__)


class MlCategorySearchWizard(models.TransientModel):
    _name = "ml.category.search.wizard"
    _description = "Wizard de búsqueda de categoría MercadoLibre"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    account_id = fields.Many2one(
        "sce.account",
        string="Cuenta ML",
        domain="[('provider_type', '=', 'mercadolibre')]",
        required=True,
    )
    publish_wizard_id = fields.Many2one("ml.publish.assistant.wizard", string="Asistente publicación", ondelete="cascade")
    query = fields.Char(string="Buscar categoría", required=True)
    result_json = fields.Text(string="Resultados JSON", readonly=True)
    result_line_ids = fields.One2many(
        "ml.category.search.result", "wizard_id", string="Resultados"
    )
    selected = fields.Boolean(string="Seleccionado")
    category_id = fields.Char(string="ID de categoría")
    category_name = fields.Char(string="Nombre de categoría")
    selected_category_id = fields.Char(string="Categoría seleccionada")
    category_attributes_json = fields.Text(string="Atributos de categoría", readonly=True)
    required_attributes_json = fields.Text(string="Atributos requeridos", readonly=True)

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

    def action_search(self):
        self.ensure_one()
        query = (self.query or "").strip()
        if not query:
            raise UserError("Debes ingresar un texto para buscar categorías.")

        provider = ProviderFactory.get_provider(self.account_id)
        result = provider.search_categories(query=query, limit=8)
        self._raise_if_access_denied_response(result, "search_categories")
        items = result.get("items") if isinstance(result, dict) else []
        if not isinstance(items, list):
            _logger.warning(
                "Respuesta inesperada en search_categories account_id=%s query=%s: %s",
                self.account_id.id,
                query,
                type(result).__name__,
            )
            items = []

        self.result_json = json.dumps(items, ensure_ascii=False, indent=2)

        try:
            self.result_line_ids.unlink()
        except Exception:
            pass

        Result = self.env["ml.category.search.result"]
        for it in items:
            cid = (it.get("category_id") or it.get("id") or "").strip()
            cname = (
                it.get("category_name") or it.get("name") or it.get("title") or ""
            ).strip()
            if not cid:
                continue
            Result.create(
                {
                    "wizard_id": self.id,
                    "category_id": cid,
                    "category_name": cname or cid,
                }
            )

        if len(items) == 1 and items[0].get("category_id"):
            self.selected_category_id = items[0]["category_id"]
            self.category_id = self.selected_category_id
            self.category_name = items[0].get("category_name") or items[0].get("name") or items[0].get("title") or self.selected_category_id
            try:
                single = self.result_line_ids.filtered(
                    lambda r: (r.category_id or "") == (self.selected_category_id or "")
                )
                if single:
                    single[0].selected = True
            except Exception:
                pass

        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.category.search.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_apply(self):
        self.ensure_one()
        selected_lines = self.result_line_ids.filtered("selected")
        if selected_lines:
            if len(selected_lines) > 1:
                raise UserError("Debes seleccionar una sola categoría.")
            self.selected_category_id = (selected_lines[0].category_id or "").strip()
            self.category_id = self.selected_category_id
            self.category_name = (selected_lines[0].category_name or "").strip() or self.category_id

        category_id = (self.selected_category_id or "").strip()
        if not category_id:
            raise UserError("Selecciona una categoría antes de aplicar.")

        provider = ProviderFactory.get_provider(self.account_id)
        attrs_res = provider.get_category_attributes(category_id=category_id)
        req_res = provider.get_category_required_fields(category_id=category_id)

        self._raise_if_access_denied_response(attrs_res, "get_category_attributes")
        self._raise_if_access_denied_response(req_res, "get_category_required_fields")

        attrs = attrs_res.get("items") if isinstance(attrs_res, dict) else []
        required = req_res.get("items") if isinstance(req_res, dict) else []
        if not isinstance(attrs, list):
            _logger.warning(
                "Respuesta inesperada en get_category_attributes account_id=%s category_id=%s: %s",
                self.account_id.id,
                category_id,
                type(attrs_res).__name__,
            )
            attrs = []
        if not isinstance(required, list):
            _logger.warning(
                "Respuesta inesperada en get_category_required_fields account_id=%s category_id=%s: %s",
                self.account_id.id,
                category_id,
                type(req_res).__name__,
            )
            required = []

        current_attrs = []
        raw_current = self.product_tmpl_id.ml_attributes_json or ""
        if raw_current:
            try:
                parsed = json.loads(raw_current)
                if isinstance(parsed, list):
                    current_attrs = [a for a in parsed if isinstance(a, dict)]
            except Exception:
                _logger.exception(
                    "Error parseando ml_attributes_json en category search wizard para product_tmpl_id=%s",
                    self.product_tmpl_id.id,
                )
                current_attrs = []

        req_ids = {(a.get("id") or "").strip() for a in required if isinstance(a, dict)}
        req_ids.discard("")
        existing_by_id = {}
        for a in current_attrs:
            aid = (a.get("id") or "").strip()
            if aid:
                existing_by_id[aid] = a

        merged = []
        for aid in sorted(req_ids):
            existing = existing_by_id.get(aid)
            if existing:
                merged.append(existing)
            else:
                merged.append({"id": aid, "value_name": ""})

        vals = {
            "ml_category_id": category_id,
            "ml_attributes_json": json.dumps(merged, ensure_ascii=False),
        }

        def _extract_value(attr_id):
            for item in merged:
                if (item.get("id") or "").strip() == attr_id:
                    return (item.get("value_name") or "").strip()
            return ""

        brand = _extract_value("BRAND")
        model = _extract_value("MODEL")
        if brand:
            vals["ml_brand"] = brand
        if model:
            vals["ml_model"] = model

        self.product_tmpl_id.write(vals)
        self.category_attributes_json = json.dumps(attrs, ensure_ascii=False, indent=2)
        self.required_attributes_json = json.dumps(required, ensure_ascii=False, indent=2)

        # Si hay wizard de publicación padre, volver a él. Si no, cerrar.
        if self.publish_wizard_id:
            category_record = self.env["ml.category"].search(
                [("account_id", "=", self.account_id.id), ("category_id", "=", category_id)],
                limit=1,
            )
            if not category_record:
                category_record = self.env["ml.category"].create(
                    {
                        "account_id": self.account_id.id,
                        "category_id": category_id,
                        "category_name": self.category_name or category_id,
                    }
                )
            self.publish_wizard_id.write(
                {"step": "base", "ml_category_ref_id": category_record.id}
            )
            return {
                "type": "ir.actions.act_window",
                "res_model": "ml.publish.assistant.wizard",
                "view_mode": "form",
                "res_id": self.publish_wizard_id.id,
                "target": "new",
            }
        else:
            return {"type": "ir.actions.act_window_close"}