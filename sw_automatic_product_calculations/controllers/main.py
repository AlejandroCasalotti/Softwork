# -*- coding: utf-8 -*-

import math

from odoo import http
from odoo.http import request


class SwAutomaticCalculationController(http.Controller):

    @http.route("/sw/calculation/add_to_cart", type="jsonrpc", auth="public", website=True, csrf=False)
    def sw_calculation_add_to_cart(self, product_template_id=None, length=0.0, width=0.0, height=0.0, total_surface=0.0, **kwargs):
        product_template_id = int(product_template_id or 0)
        length = float(length or 0.0)
        width = float(width or 0.0)
        height = float(height or 0.0)
        total_surface = float(total_surface or 0.0)

        if product_template_id <= 0:
            return {"ok": False, "message": "Producto inválido."}

        template = request.env["product.template"].sudo().browse(product_template_id)
        if not template.exists():
            return {"ok": False, "message": "Producto no encontrado."}

        if not template.website_enable_calculator or not template.website_calculation_method_id:
            return {"ok": False, "message": "Este producto no tiene cálculo web habilitado."}

        method = template.website_calculation_method_id.sudo()
        if not method.active:
            return {"ok": False, "message": "El método de cálculo no está activo."}

        if total_surface <= 0:
            if length <= 0 or width <= 0:
                return {"ok": False, "message": "Largo y ancho deben ser mayores a cero o debe informar Total."}
            if method.method_type == "m3" and height <= 0:
                return {"ok": False, "message": "Alto debe ser mayor a cero para cálculo m3 o debe informar Total."}
            total_surface = length * width * (height if method.method_type == "m3" else 1.0)

        order = request.website.sale_get_order(force_create=True)
        if not order:
            return {"ok": False, "message": "No se pudo obtener el carrito."}

        added_lines = []

        for line in method.line_ids:
            qty = (line.quantity_per_unit or 0.0) * total_surface
            if line.quantity_type == "integer":
                qty = float(math.ceil(qty))
            if qty <= 0:
                continue

            order._cart_update(
                product_id=line.product_id.id,
                add_qty=qty,
                set_qty=0,
            )
            added_lines.append({
                "product_id": line.product_id.id,
                "product_name": line.product_id.display_name,
                "qty": qty,
            })

        featured_product = template.product_variant_id
        if featured_product:
            featured_line = method.line_ids.filtered(lambda l: l.product_id.id == featured_product.id)[:1]
            if featured_line:
                featured_qty = (featured_line.quantity_per_unit or 0.0) * total_surface
                if featured_line.quantity_type == "integer":
                    featured_qty = float(math.ceil(featured_qty))
            else:
                featured_qty = total_surface

            if featured_qty > 0:
                order._cart_update(
                    product_id=featured_product.id,
                    add_qty=featured_qty,
                    set_qty=0,
                )
                added_lines.append({
                    "product_id": featured_product.id,
                    "product_name": featured_product.display_name,
                    "qty": featured_qty,
                })

        return {
            "ok": True,
            "message": "Productos agregados al carrito.",
            "method_type": method.method_type,
            "total_surface": total_surface,
            "added_lines": added_lines,
            "cart_quantity": order.cart_quantity,
        }