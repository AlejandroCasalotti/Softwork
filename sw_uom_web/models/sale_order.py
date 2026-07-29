# -*- coding: utf-8 -*-

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_update(
        self,
        product_id=None,
        line_id=None,
        add_qty=0,
        set_qty=0,
        product_custom_attribute_values=None,
        no_variant_attribute_values=None,
        **kwargs
    ):
        """
        Fuerza la UoM web en el carrito cuando el producto tiene activo
        el modo de venta web por UoM.
        """
        if product_id:
            product = self.env["product.product"].browse(int(product_id))
            tmpl = product.product_tmpl_id
            if tmpl and tmpl.web_uom_sale_mode and tmpl.web_sale_uom_id:
                kwargs["uom_id"] = tmpl.web_sale_uom_id.id

        return super()._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            **kwargs
        )