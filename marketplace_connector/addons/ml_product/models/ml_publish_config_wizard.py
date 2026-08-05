# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class MlPublishConfigWizard(models.TransientModel):
    _name = "ml.publish.config.wizard"
    _description = "Configuración UX de publicación MercadoLibre"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    account_id = fields.Many2one("sce.account", string="Cuenta ML", readonly=True)

    ml_listing_type = fields.Char(string="Tipo de publicación")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
    )
    ml_warranty = fields.Char(string="Garantía")
    ml_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Forma de envío",
        default="me2",
    )

    ml_pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    ml_use_pricelist_price = fields.Boolean(string="Usar precio desde lista", default=True)
    ml_manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    ml_price = fields.Float(string="Precio manual ML")

    ml_stock_reserve_qty = fields.Float(string="Stock reservado para Odoo", default=0.0)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        product_id = self.env.context.get("default_product_tmpl_id")
        if not product_id:
            return vals
        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            return vals

        account = product.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay cuenta SCE MercadoLibre activa configurada.")

        vals.update(
            {
                "product_tmpl_id": product.id,
                "account_id": account.id,
                "ml_listing_type": product.ml_listing_type,
                "ml_condition": product.ml_condition,
                "ml_warranty": product.ml_warranty,
                "ml_shipping_mode": product.ml_shipping_mode or "me2",
                "ml_pricelist_id": product.ml_pricelist_id.id if product.ml_pricelist_id else False,
                "ml_use_pricelist_price": product.ml_use_pricelist_price,
                "ml_manual_price_override": product.ml_manual_price_override,
                "ml_price": product.ml_price,
                "ml_stock_reserve_qty": product.ml_stock_reserve_qty,
            }
        )
        return vals

    def action_apply(self):
        self.ensure_one()
        self.product_tmpl_id.write(
            {
                "ml_listing_type": self.ml_listing_type or "gold_special",
                "ml_condition": self.ml_condition or "new",
                "ml_warranty": self.ml_warranty or False,
                "ml_shipping_mode": self.ml_shipping_mode or "me2",
                "ml_pricelist_id": self.ml_pricelist_id.id if self.ml_pricelist_id else False,
                "ml_use_pricelist_price": bool(self.ml_use_pricelist_price),
                "ml_manual_price_override": bool(self.ml_manual_price_override),
                "ml_price": self.ml_price if self.ml_manual_price_override else self.product_tmpl_id.ml_price,
                "ml_stock_reserve_qty": max(0.0, self.ml_stock_reserve_qty or 0.0),
            }
        )
        return {"type": "ir.actions.act_window_close"}