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

    def action_search(self):
        self.ensure_one()
        query = (self.query or "").strip()
        if not query:
            raise UserError("Debes ingresar un texto para buscar categorías.")

        provider = ProviderFactory.get_provider(self.account_id)
        result = provider.search_categories(query=query, limit=20)
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
        self.product_tmpl_id.write({"ml_category_id": category_id})
        return {"type": "ir.actions.act_window_close"}