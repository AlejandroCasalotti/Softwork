# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def clean_provider_lines(self):
        """
        Remove or adjust payment provider product lines
        depending on the state of the order.
        """
        provider_products = self.env['payment.provider'].sudo().search([]).mapped('product_id')
        for order in self:
            if not order.state == 'sale':
                order.order_line.filtered(lambda l: l.product_id in provider_products).unlink()
