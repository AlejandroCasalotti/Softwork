# -*- coding: utf-8 -*-
import json

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory


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
    query = fields.Char(string="Buscar categoría", required=True)
    result_json = fields.Text(string="Resultados JSON", readonly=True)
    selected_category_id = fields.Char(string="Categoría seleccionada")
    category_attributes_json = fields.Text(string="Atributos de categoría", readonly=True)
    required_attributes_json = fields.Text(string="Atributos requeridos", readonly=True)

    def action_search(self):
        self.ensure_one()
        query = (self.query or "").strip()
        if not query:
            raise UserError("Debes ingresar un texto para buscar categorías.")

        provider = ProviderFactory.get_provider(self.account_id)
        result = provider.search_categories(query=query, limit=8)
        items = result.get("items") if isinstance(result, dict) else []
        if not isinstance(items, list):
            items = []

        self.result_json = json.dumps(items, ensure_ascii=False, indent=2)

        if len(items) == 1 and items[0].get("category_id"):
            self.selected_category_id = items[0]["category_id"]

        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.category.search.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_apply(self):
        self.ensure_one()
        category_id = (self.selected_category_id or "").strip()
        if not category_id:
            raise UserError("Selecciona o ingresa una categoría antes de aplicar.")

        provider = ProviderFactory.get_provider(self.account_id)
        attrs_res = provider.get_category_attributes(category_id=category_id)
        req_res = provider.get_category_required_fields(category_id=category_id)

        attrs = attrs_res.get("items") if isinstance(attrs_res, dict) else []
        required = req_res.get("items") if isinstance(req_res, dict) else []
        if not isinstance(attrs, list):
            attrs = []
        if not isinstance(required, list):
            required = []

        current_attrs = []
        raw_current = self.product_tmpl_id.ml_attributes_json or ""
        if raw_current:
            try:
                parsed = json.loads(raw_current)
                if isinstance(parsed, list):
                    current_attrs = [a for a in parsed if isinstance(a, dict)]
            except Exception:
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

        return {"type": "ir.actions.act_window_close"}