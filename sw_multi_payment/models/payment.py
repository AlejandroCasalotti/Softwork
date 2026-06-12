# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Línea de diarios adicionales
    additional_journal_ids = fields.Many2many(
        'account.journal',
        'payment_additional_journal',
        'payment_id',
        'journal_id',
        string='Métodos de Pago Adicionales'
    )
    
    # Monto por cada diario adicional
    additional_amount_ids = fields.One2many(
        'account.payment.additional',
        'payment_id',
        string='Detalle de Pagos'
    )
    
    # Total
    total_payment = fields.Float(
        string='Total',
        compute='_compute_total_payment',
        store=True
    )

    @api.depends('amount', 'additional_amount_ids.amount')
    def _compute_total_payment(self):
        for rec in self:
            add_amount = sum(rec.additional_amount_ids.mapped('amount'))
            rec.total_payment = rec.amount + add_amount


class PaymentAdditional(models.Model):
    _name = 'account.payment.additional'
    _description = 'Pago Adicional'

    payment_id = fields.Many2one(
        'account.payment',
        string='Pago',
        required=True,
        ondelete='cascade'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True
    )
    amount = fields.Float(
        string='Monto',
        required=True
    )
    reference = fields.Char(string='Referencia')