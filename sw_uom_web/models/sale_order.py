# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


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
        Fuerza la UoM web en backend (server-side), independientemente
        de lo que envíe el frontend.
        """
        forced_uom_id = False
        if product_id:
            product = self.env["product.product"].browse(int(product_id))
            tmpl = product.product_tmpl_id
            if tmpl:
                if getattr(tmpl, "web_uom_sale_mode", False) and getattr(tmpl, "web_sale_uom_id", False):
                    forced_uom_id = tmpl.web_sale_uom_id.id
                else:
                    allowed = getattr(tmpl, "web_allowed_uom_ids", False) or getattr(tmpl, "web_allowed_packaging_ids", False)
                    if allowed:
                        forced_uom_id = allowed[0].id

        if forced_uom_id:
            # Forzar todas las posibles keys usadas por website/cart
            kwargs["uom_id"] = forced_uom_id
            kwargs["uom"] = forced_uom_id
            kwargs["product_uom"] = forced_uom_id
            _logger.info("SW UoM Web: forcing uom %s (incoming keys=%s)", forced_uom_id, list(kwargs.keys()))

        res = super()._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            **kwargs
        )

        # Refuerzo post-super: asegurar que la línea quede en UoM permitida
        if forced_uom_id and isinstance(res, dict):
            line_id_res = res.get("line_id") or line_id
            if line_id_res:
                line = self.env["sale.order.line"].sudo().browse(int(line_id_res))
                if line.exists() and line.product_uom.id != forced_uom_id:
                    line.write({"product_uom": forced_uom_id})

        return res