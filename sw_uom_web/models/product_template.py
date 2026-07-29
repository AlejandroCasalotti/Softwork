# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    web_allowed_packaging_ids = fields.Many2many(
        "product.packaging.level",
        "product_tmpl_web_packaging_rel",
        "product_tmpl_id",
        "packaging_id",
        string="Embalajes permitidos en web",
        help="Si se seleccionan embalajes, en el sitio web solo se mostrarán estos para el producto. "
             "Si queda vacío, se mostrarán todos (comportamiento estándar).",
    )

    @api.constrains("web_allowed_packaging_ids")
    def _check_web_allowed_packaging_ids(self):
        for rec in self:
            invalid = rec.web_allowed_packaging_ids.filtered(
                lambda p: p.product_id.product_tmpl_id != rec
            )
            if invalid:
                raise ValidationError(
                    "Solo puede seleccionar embalajes que pertenezcan al mismo producto."
                )