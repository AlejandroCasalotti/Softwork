# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def print_receipt(self):
        """Imprimir comprobante"""
        return self.env.ref('sw_multi_payment.report_payment_receipt').report_action(self)


class ReportPaymentReceipt(models.AbstractModel):
    _name = 'report.sw_multi_payment.report_payment_receipt'
    _description = 'Report Payment Receipt'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.payment'].browse(docids)
        
        return {
            'docs': docs,
            'doc_model': 'account.payment',
        }