# -*- coding: utf-8 -*-
import json

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory


class MlCategorySearchWizard(models.TransientModel):
    _name = "ml.category.search.wizard"
    _description = "Wizard de búsqueda de categoría MercadoLibre"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    publication_id = fields.Many2one("marketplace.publication", readonly=True, ondelete="cascade")
    account_id = fields.Many2one("sce.account", string="Cuenta ML", required=True)
    publish_wizard_id = fields.Many2one("ml.publish.assistant.wizard", ondelete="cascade")
    query = fields.Char(string="Buscar categoría", required=True)
    result_json = fields.Text(string="Resultados JSON", readonly=True)
    result_line_ids = fields.One2many("ml.category.search.result", "wizard_id", string="Resultados")
    selected_category_id = fields.Char(string="Categoría seleccionada")
    category_name = fields.Char(string="Nombre de categoría")

    def action_search(self):
        self.ensure_one()
        if not (self.query or "").strip():
            raise UserError("Debes ingresar un texto para buscar categorías.")
        response = ProviderFactory.get_provider(self.account_id).search_categories(query=self.query.strip(), limit=8)
        items = response.get("items") if isinstance(response, dict) else []
        if not isinstance(items, list):
            items = []
        self.result_line_ids.unlink()
        self.result_json = json.dumps(items, ensure_ascii=False, indent=2)
        for item in items:
            if not isinstance(item, dict):
                continue
            category_id = (item.get("category_id") or item.get("id") or "").strip()
            if category_id:
                self.env["ml.category.search.result"].create(
                    {
                        "wizard_id": self.id,
                        "category_id": category_id,
                        "category_name": (item.get("category_name") or item.get("name") or category_id).strip(),
                    }
                )
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}

    def action_apply(self):
        self.ensure_one()
        selected = self.result_line_ids.filtered("selected")
        if len(selected) != 1:
            raise UserError("Debes seleccionar una sola categoría.")
        category = selected
        response = ProviderFactory.get_provider(self.account_id).get_category_required_fields(category_id=category.category_id)
        required = response.get("items") if isinstance(response, dict) else []
        attributes = [{"id": item.get("id"), "value_name": ""} for item in required if isinstance(item, dict) and item.get("id")]
        if self.publication_id:
            self.publication_id.write(
                {
                    "category_ref": category.category_id,
                    "category_name": category.category_name,
                    "attributes_json": json.dumps(attributes, ensure_ascii=False),
                    "state": "category",
                }
            )
        if self.publish_wizard_id:
            category_record = self.env["ml.category"].search(
                [("account_id", "=", self.account_id.id), ("category_id", "=", category.category_id)], limit=1
            )
            if not category_record:
                category_record = self.env["ml.category"].create(
                    {"account_id": self.account_id.id, "category_id": category.category_id, "category_name": category.category_name}
                )
            self.publish_wizard_id.write({"step": "base", "ml_category_ref_id": category_record.id})
            return {"type": "ir.actions.act_window", "res_model": "ml.publish.assistant.wizard", "view_mode": "form", "res_id": self.publish_wizard_id.id, "target": "new"}
        return {"type": "ir.actions.act_window_close"}