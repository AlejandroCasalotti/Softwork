# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sw_web_uom_ratio = fields.Float(
        string="SW Web UoM Ratio",
        digits=(16, 6),
        default=1.0,
        help="Ratio de la UoM seleccionada en web para calcular precio por UoM base en carrito.",
    )

    def _get_allowed_uom_for_product(self, product, preferred_uom_id=False):
        tmpl = product.product_tmpl_id
        if getattr(tmpl, "web_uom_sale_mode", False) and getattr(tmpl, "web_sale_uom_id", False):
            return tmpl.web_sale_uom_id

        allowed = getattr(tmpl, "web_allowed_uom_ids", False) or getattr(tmpl, "web_allowed_packaging_ids", False)
        if not allowed:
            return self.env["uom.uom"]

        if preferred_uom_id:
            preferred = allowed.filtered(lambda u: u.id == int(preferred_uom_id))
            if preferred:
                return preferred[:1]

        return allowed[:1]

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            product_id = vals.get("product_id")
            if product_id:
                product = self.env["product.product"].browse(product_id)
                preferred_uom_id = vals.get("product_uom_id")
                allowed_uom = self._get_allowed_uom_for_product(product, preferred_uom_id=preferred_uom_id)
                if allowed_uom and (not preferred_uom_id or allowed_uom.id != int(preferred_uom_id)):
                    vals["product_uom_id"] = allowed_uom.id
            new_vals_list.append(vals)
        return super().create(new_vals_list)

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if not line.product_id:
                continue
            preferred_uom_id = vals.get("product_uom_id") or line.product_uom_id.id
            allowed_uom = self._get_allowed_uom_for_product(line.product_id, preferred_uom_id=preferred_uom_id)
            current_uom = getattr(line, "product_uom_id", False)
            if allowed_uom and current_uom and current_uom.id != allowed_uom.id:
                super(SaleOrderLine, line).write({"product_uom_id": allowed_uom.id})
        return res