# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    payment_charges = fields.Float(string='Payment Charges')
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    