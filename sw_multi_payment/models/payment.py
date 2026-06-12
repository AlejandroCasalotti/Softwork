# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PaymentMethodLine(models.Model):
    _name = 'payment.multi.method.line'
    _description = 'Línea de Método de Pago'

    payment_id = fields.Many2one(
        'account.payment',
        string='Pago',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='#', default=10)
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True
    )
    amount = fields.Float(
        string='Monto',
        required=True,
        default=0.0
    )
    reference = fields.Char(string='Referencia')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Líneas de pago múltiples
    multi_line_ids = fields.One2many(
        'payment.multi.method.line',
        'payment_id',
        string='Métodos de Pago',
        copy=True
    )
    
    # Monto total
    multi_total = fields.Float(
        string='Monto Total',
        compute='_compute_multi_total',
        store=True
    )

    @api.depends('multi_line_ids.amount')
    def _compute_multi_total(self):
        for rec in self:
            rec.multi_total = sum(rec.multi_line_ids.mapped('amount'))