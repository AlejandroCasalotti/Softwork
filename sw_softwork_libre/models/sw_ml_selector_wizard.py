# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class SwMlSelectorWizard(models.TransientModel):
    _name = "sw.ml.selector.wizard"
    _description = "Selector opciones MercadoLibre"

    selector_type = fields.Selection(
        [
            ("catalog", "Catálogo"),
            ("fee", "Cargo por vender / cuotas"),
            ("shipping", "Forma de entrega"),
            ("warranty", "Garantía"),
        ],
        required=True,
    )
    product_tmpl_id = fields.Many2one("product.template", required=True)
    option_key = fields.Char(string="Clave opción")
    option_label = fields.Char(string="Descripción", required=True)
    option_payload = fields.Text(string="Payload")

    def action_confirm(self):
        self.ensure_one()
        product = self.product_tmpl_id
        if not product:
            raise UserError("No se encontró el producto destino.")

        if self.selector_type == "catalog":
            product.write({
                "ml_listing_description": self.option_label,
                "ml_selected_catalog_detail": self.option_label,
            })
        elif self.selector_type == "fee":
            product.write({
                "ml_fee_option_id": self.option_key or self.option_label,
                "ml_selected_fee_detail": self.option_label,
            })
        elif self.selector_type == "shipping":
            product.write({
                "ml_shipping_mode": self.option_key or self.option_label,
                "ml_selected_shipping_detail": self.option_label,
            })
        elif self.selector_type == "warranty":
            product.write({
                "ml_warranty_type": self.option_key or self.option_label,
                "ml_selected_warranty_detail": self.option_label,
            })
        return {"type": "ir.actions.act_window_close"}