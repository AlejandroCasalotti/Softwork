# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    journal_line_ids = fields.One2many(
        'account.payment.journal.line',
        'payment_id',
        string='Métodos de Pago'
    )
    
    total_amount = fields.Float(
        string='Total',
        compute='_compute_total_amount',
        store=True
    )

    @api.depends('amount', 'journal_line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            add_amount = sum(rec.journal_line_ids.mapped('amount'))
            rec.total_amount = rec.amount + add_amount


class PaymentJournalLine(models.Model):
    _name = 'account.payment.journal.line'
    _description = 'Línea de Diario de Pago'

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