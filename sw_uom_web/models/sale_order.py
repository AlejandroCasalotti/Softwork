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
            if tmpl:
                # Flujo legacy/compatibilidad: modo forzado por campo dedicado
                if getattr(tmpl, "web_uom_sale_mode", False) and getattr(tmpl, "web_sale_uom_id", False):
                    kwargs["uom_id"] = tmpl.web_sale_uom_id.id
                else:
                    # Flujo nuevo: usar selección web_allowed_uom_ids / web_allowed_packaging_ids
                    allowed = getattr(tmpl, "web_allowed_uom_ids", False) or getattr(tmpl, "web_allowed_packaging_ids", False)
                    if allowed:
                        kwargs["uom_id"] = allowed[0].id

        return super()._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            **kwargs
        )