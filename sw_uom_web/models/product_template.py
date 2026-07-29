# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    web_allowed_packaging_ids = fields.Many2many(
        "uom.uom",
        "product_tmpl_web_uom_rel",
        "product_tmpl_id",
        "uom_id",
        string="Embalajes permitidos en web",
        help="Si se seleccionan embalajes, en el sitio web solo se mostrarán estos para el producto. "
             "Si queda vacío, se mostrarán todos (comportamiento estándar).",
    )

    @api.constrains("web_allowed_packaging_ids")
    def _check_web_allowed_packaging_ids(self):
        for rec in self:
            invalid = rec.web_allowed_packaging_ids.filtered(
                lambda u: u not in rec.uom_ids
            )
            if invalid:
                raise ValidationError(
                    "Solo puede seleccionar UoM/embalajes que estén cargados en uom_ids del producto."
                )