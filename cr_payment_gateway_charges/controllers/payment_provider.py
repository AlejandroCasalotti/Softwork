# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
 
from odoo.http import request, route
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers import main
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.payment.controllers.portal import PaymentPortal


class CustomPaymentCharge(http.Controller):

    @route(['/update/order_line'], type='jsonrpc', methods=['POST'], auth="public", website=True, csrf=False)
    def payment_gateway(self, **post):
        """
            Update the sale order line by applying payment gateway charges.

            - Identifies the active order from orderId, sale_order_name, or current website cart.
            - Validates the payment provider and ensures it has an associated product.
            - Removes any existing payment charge lines from the order.
            - Calculates the charge as a percentage of the order total based on provider settings.
            - Updates the provider's product price with the calculated charge.
            - Creates a new sale order line for the payment gateway charge.
            - Returns a JSON response with updated order details and the newly added line ID.
        """

        # order_sudo = request.website._create_cart()
        order_sudo = request.cart
        provider_id = post.get('provider_id')
        sale_order_name = post.get('sale_order_id')
        orderId = post.get('orderId')
        SaleOrder = request.env['sale.order'].sudo()
        order_id = False
        
        if orderId:
            try:
                order_id = SaleOrder.browse(int(orderId))
                if not order_id.exists():
                    order_id = False
            except Exception:
                order_id = False

        sale_order = False
        if sale_order_name:
            sale_order = SaleOrder.search([('name', '=', sale_order_name)], limit=1)

        active_order = order_id or sale_order or order_sudo

        if not provider_id or not active_order:
            return {"error": "Missing provider_id or order not found."}

        provider_id = int(provider_id)
        payment_provider = request.env['payment.provider'].sudo().browse(provider_id)
        if not payment_provider.exists():
            return {"error": "Invalid provider_id."}

        payment_provider_product_ids = request.env['payment.provider'].sudo().search([
            ('product_id', '!=', False),
            ('state', 'in', ['enabled', 'test']),
        ]).mapped('product_id').ids or []

        existing_charge_line = active_order.order_line.filtered(
            lambda x: x.product_id.id in payment_provider_product_ids
        )
        if existing_charge_line:
            existing_charge_line.unlink()
        charge_percent = (payment_provider.payment_charges * active_order.amount_total) / 100

        payment_provider.product_id.sudo().write({'lst_price': charge_percent})
        payment_product = payment_provider.product_id
        order_line = request.env['sale.order.line'].sudo().create({
            'order_id': active_order.id,
            'product_id': payment_product.id,
            'price_unit': charge_percent,
            'name': payment_product.name,
            'product_uom_qty': 1,
        })
        return {
            "success": True,
            "order": self._update_order_line(active_order.sudo(), charge_percent),
            "added_line": order_line.id,
        }

    def _update_order_line(self, order, charge_percent):
        return {
            "amount_total": order.amount_total,
            "amount_untaxed": order.amount_untaxed,
            "currency": order.currency_id.symbol,
            "cart_quantity": order.cart_quantity,
            "charged_amount": charge_percent,
            "order_lines": [
                {
                    "line_id": line.id,
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "name_short": line.name_short,
                    "product_uom_qty": line.product_uom_qty,
                    "price_subtotal": line.price_subtotal,
                    "currency": order.currency_id.symbol,
                    "image_128": line.product_id.image_128.decode() if line.product_id.image_128 else "",
                }
                for line in order.order_line
            ]
        }


class ShopPayment(main.WebsiteSale):
    
    @route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment_custom(self, **post):
        res = super(ShopPayment, self).shop_payment(**post)
        # order_sudo = request.website._create_cart()
        order_sudo = request.cart
        if order_sudo:
            order_sudo.clean_provider_lines()
        return res

class CustomSalePortal(CustomerPortal):

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(self, order_id=None, access_token=None, **kwargs):
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        res = super().portal_order_page(order_id=order_id, access_token=access_token, **kwargs)
        if order_sudo:
            order_sudo.clean_provider_lines()
        return res


class CustomWebsiteSale(WebsiteSale):

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, access_token=None, revive='', **post):
        # order_sudo = request.website._create_cart()
        order_sudo = request.cart
        if order_sudo:
            order_sudo.clean_provider_lines()
        return super().cart(access_token=access_token, revive=revive, **post)

class CustomPaymentPortal(PaymentPortal):

    @http.route(
        '/payment/pay', type='http', methods=['GET'], auth='public', website=True, sitemap=False,
    )
    def payment_pay(
        self, reference=None, amount=None, currency_id=None, partner_id=None, company_id=None,
        access_token=None, **kwargs
    ):
        res = super().payment_pay(
                reference=reference, amount=amount, currency_id=currency_id,
                partner_id=partner_id, company_id=company_id,
                access_token=access_token, **kwargs
            )
        order_sudo = request.env['sale.order'].sudo().browse(int(kwargs.get("sale_order_id")))
        if order_sudo:
            order_sudo.clean_provider_lines()
        return res
