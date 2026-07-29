# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    web_min_sale_qty = fields.Float(
        string="Cantidad mínima de venta web",
        digits="Product Unit of Measure",
        help="Cantidad mínima en la UoM de venta web (ej: 2.20 para caja x 2.20 m2).",
    )
    web_sale_uom_id = fields.Many2one(
        "uom.uom",
        string="UoM de venta web",
        help="UoM/embalaje que se utilizará en el sitio web para vender este producto.",
    )
    web_uom_sale_mode = fields.Boolean(
        string="Modo venta web por UoM",
        compute="_compute_web_uom_sale_mode",
        store=False,
    )
    web_sale_uom_price = fields.Float(
        string="Precio por UoM web",
        compute="_compute_web_sale_uom_price",
        digits="Product Price",
        store=False,
    )
    web_sale_uom_total_text = fields.Char(
        string="Leyenda venta web por UoM",
        compute="_compute_web_sale_uom_total_text",
        store=False,
    )

    @api.depends("web_min_sale_qty", "web_sale_uom_id")
    def _compute_web_uom_sale_mode(self):
        for rec in self:
            rec.web_uom_sale_mode = bool(rec.web_min_sale_qty and rec.web_min_sale_qty > 0 and rec.web_sale_uom_id)

    @api.depends("list_price", "uom_id", "web_sale_uom_id")
    def _compute_web_sale_uom_price(self):
        for rec in self:
            if rec.web_sale_uom_id and rec.uom_id:
                rec.web_sale_uom_price = rec.uom_id._compute_price(rec.list_price or 0.0, rec.web_sale_uom_id)
            else:
                rec.web_sale_uom_price = 0.0

    @api.depends("web_uom_sale_mode", "web_sale_uom_id", "web_sale_uom_price")
    def _compute_web_sale_uom_total_text(self):
        for rec in self:
            if rec.web_uom_sale_mode and rec.web_sale_uom_id:
                amount = formatLang(rec.env, rec.web_sale_uom_price, currency_obj=rec.currency_id) if rec.currency_id else ("%.2f" % rec.web_sale_uom_price)
                rec.web_sale_uom_total_text = 'Este producto es vendido en "%s" a "%s"' % (
                    rec.web_sale_uom_id.display_name,
                    amount,
                )
            else:
                rec.web_sale_uom_total_text = False

    @api.constrains("web_min_sale_qty", "web_sale_uom_id")
    def _check_web_uom_fields_consistency(self):
        for rec in self:
            has_qty = bool(rec.web_min_sale_qty and rec.web_min_sale_qty > 0)
            has_uom = bool(rec.web_sale_uom_id)
            if has_qty != has_uom:
                raise ValidationError(
                    "Para usar venta web por UoM, debe completar ambos campos: "
                    "'Cantidad mínima de venta web' y 'UoM de venta web'."
                )