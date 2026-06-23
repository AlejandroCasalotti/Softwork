# -*- coding: utf-8 -*-

import math

from odoo import http
from odoo.http import request


class SwAutomaticCalculationController(http.Controller):

    def _resolve_context(self, product_template_id=None, method_id=None, length=0.0, width=0.0, height=0.0, total_surface=0.0):
        product_template_id = int(product_template_id or 0)
        method_id = int(method_id or 0)
        length = float(length or 0.0)
        width = float(width or 0.0)
        height = float(height or 0.0)
        total_surface = float(total_surface or 0.0)

        if product_template_id <= 0:
            return {"ok": False, "message": "Producto inválido."}

        template = request.env["product.template"].sudo().browse(product_template_id)
        if not template.exists():
            return {"ok": False, "message": "Producto no encontrado."}

        if not template.website_enable_calculator:
            return {"ok": False, "message": "Este producto no tiene cálculo web habilitado."}

        allowed_methods = template.website_calculation_method_ids
        if not allowed_methods and template.website_calculation_method_id:
            allowed_methods = template.website_calculation_method_id

        if not allowed_methods:
            return {"ok": False, "message": "Este producto no tiene métodos de cálculo configurados."}

        if method_id > 0:
            method = request.env["calculation.method"].sudo().browse(method_id)
            if not method.exists():
                return {"ok": False, "message": "Método de cálculo no encontrado."}
            if method not in allowed_methods:
                return {"ok": False, "message": "El método seleccionado no está permitido para este producto."}
        else:
            method = allowed_methods[0]

        method = method.sudo()
        if not method.active:
            return {"ok": False, "message": "El método de cálculo no está activo."}

        if total_surface <= 0:
            if length <= 0 or width <= 0:
                return {"ok": False, "message": "Largo y ancho deben ser mayores a cero o debe informar Total."}
            if method.method_type == "m3" and height <= 0:
                return {"ok": False, "message": "Alto debe ser mayor a cero para cálculo m3 o debe informar Total."}
            total_surface = length * width * (height if method.method_type == "m3" else 1.0)

        computed_lines = []
        for line in method.line_ids:
            qty = (line.quantity_per_unit or 0.0) * total_surface
            if line.quantity_type == "integer":
                qty = float(math.ceil(qty))
            if qty <= 0:
                continue
            computed_lines.append({
                "product_id": line.product_id.id,
                "product_name": line.product_id.display_name,
                "product_image_url": f"/web/image/product.product/{line.product_id.id}/image_128",
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
                factor = template.website_m3_factor if method.method_type == "m3" else template.website_m2_factor
                featured_qty = total_surface * (factor or 0.0)

            if featured_qty > 0:
                computed_lines.append({
                    "product_id": featured_product.id,
                    "product_name": featured_product.display_name,
                    "product_image_url": f"/web/image/product.product/{featured_product.id}/image_128",
                    "qty": featured_qty,
                })

        return {
            "ok": True,
            "template": template,
            "method": method,
            "total_surface": total_surface,
            "computed_lines": computed_lines,
        }

    @http.route("/sw/calculation/preview", type="jsonrpc", auth="public", website=True, csrf=False)
    def sw_calculation_preview(self, product_template_id=None, method_id=None, length=0.0, width=0.0, height=0.0, total_surface=0.0, **kwargs):
        ctx = self._resolve_context(
            product_template_id=product_template_id,
            method_id=method_id,
            length=length,
            width=width,
            height=height,
            total_surface=total_surface,
        )
        if not ctx.get("ok"):
            return ctx

        return {
            "ok": True,
            "message": "Cálculo realizado.",
            "method_type": ctx["method"].method_type,
            "total_surface": ctx["total_surface"],
            "added_lines": ctx["computed_lines"],
        }

    @http.route("/sw/calculation/add_to_cart", type="jsonrpc", auth="public", website=True, csrf=False)
    def sw_calculation_add_to_cart(self, product_template_id=None, method_id=None, length=0.0, width=0.0, height=0.0, total_surface=0.0, lines=None, **kwargs):
        ctx = self._resolve_context(
            product_template_id=product_template_id,
            method_id=method_id,
            length=length,
            width=width,
            height=height,
            total_surface=total_surface,
        )
        if not ctx.get("ok"):
            return ctx

        order = request.env["sale.order"].sudo().search([
            ("partner_id", "=", request.website.partner_id.id),
            ("state", "=", "draft"),
            ("website_id", "=", request.website.id),
        ], limit=1)

        if not order:
            website_partner = request.website.partner_id
            if not website_partner:
                return {"ok": False, "message": "No se pudo resolver partner del website."}

            default_pricelist = request.website.pricelist_id or request.env["product.pricelist"].sudo().search([], limit=1)
            order_vals = {
                "partner_id": website_partner.id,
                "company_id": request.website.company_id.id or request.env.company.id,
                "website_id": request.website.id,
            }
            if default_pricelist:
                order_vals["pricelist_id"] = default_pricelist.id

            order = request.env["sale.order"].sudo().create(order_vals)

        if not order:
            return {"ok": False, "message": "No se pudo obtener/crear el carrito."}

        selected_lines = lines or ctx["computed_lines"]
        if not isinstance(selected_lines, list):
            return {"ok": False, "message": "Formato de líneas inválido."}

        method_products = set(ctx["method"].sudo().line_ids.mapped("product_id").ids)
        if ctx["template"].product_variant_id:
            method_products.add(ctx["template"].product_variant_id.id)

        added_lines = []
        for line in selected_lines:
            try:
                product_id = int((line or {}).get("product_id") or 0)
                qty = float((line or {}).get("qty") or 0.0)
            except Exception:
                continue

            if product_id <= 0 or qty <= 0:
                continue
            if product_id not in method_products:
                continue

            product = request.env["product.product"].sudo().browse(product_id)
            if not product.exists():
                continue

            existing_line = order.order_line.filtered(lambda l: l.product_id.id == product_id)[:1]
            if existing_line:
                existing_line.sudo().write({
                    "product_uom_qty": (existing_line.product_uom_qty or 0.0) + qty,
                })
            else:
                request.env["sale.order.line"].sudo().create({
                    "order_id": order.id,
                    "product_id": product_id,
                    "product_uom_qty": qty,
                    "name": product.display_name,
                    "price_unit": product.lst_price,
                    "customer_lead": 0.0,
                    "product_uom_id": product.uom_id.id,
                    "order_partner_id": order.partner_id.id,
                })

            added_lines.append({
                "product_id": product.id,
                "product_name": product.display_name,
                "product_image_url": f"/web/image/product.product/{product.id}/image_128",
                "qty": qty,
            })

        if not added_lines:
            return {"ok": False, "message": "No hay líneas válidas para agregar al carrito."}

        return {
            "ok": True,
            "message": "Productos agregados al carrito.",
            "method_type": ctx["method"].method_type,
            "total_surface": ctx["total_surface"],
            "added_lines": added_lines,
            "cart_quantity": order.cart_quantity,
        }