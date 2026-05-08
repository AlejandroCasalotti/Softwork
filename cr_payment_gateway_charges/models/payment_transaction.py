# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models

class PaymentTransactionInherit(models.Model):
    _inherit = 'payment.transaction'

    def _get_processing_values(self):
        """ update the amount """
        self.ensure_one()
        processing_values = super()._get_processing_values()
        sale_order_id = self.env['sale.order'].search([
                ('transaction_ids', 'in', self.id),
            ])
        if sale_order_id:
            self.sudo().write({'amount': sale_order_id.amount_total})
            processing_values['amount'] = sale_order_id.amount_total

        return processing_values
