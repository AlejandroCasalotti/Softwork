# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PaymentMethodLine(models.Model):
    _name = 'payment.method.line'
    _description = 'Línea de Método de Pago'
    _order = 'sequence'

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
    method_line_ids = fields.One2many(
        'payment.method.line',
        'payment_id',
        string='Métodos de Pago',
        copy=True,
        deprecated="Usar método único o múltiples"
    )
    
    # Monto total (calculado)
    total_amount = fields.Float(
        string='Monto Total',
        compute='_compute_total_amount',
        store=True
    )
    
    # indicar si es pago múltiple
    is_multi = fields.Boolean(
        string='Pago Múltiple',
        default=False
    )

    @api.depends('method_line_ids.amount', 'is_multi', 'amount')
    def _compute_total_amount(self):
        for rec in self:
            if rec.is_multi and rec.method_line_ids:
                rec.total_amount = sum(rec.method_line_ids.mapped('amount'))
            else:
                rec.total_amount = rec.amount

    def action_post(self):
        """Publicar el pago"""
        if self.is_multi and self.method_line_ids:
            # Crear un pago por cada línea
            for line in self.method_line_ids:
                payment = self.copy()
                payment.write({
                    'journal_id': line.journal_id.id,
                    'amount': line.amount,
                    'ref': line.reference or self.ref,
                })
                payment.action_post()
            
            # Cancelar el pago original
            self.button_canceled()
        else:
            return super(AccountPayment, self).action_post()
        
        return True

    def action_draft(self):
        """Volver a borrador"""
        if self.is_multi and self.method_line_ids:
            self.write({'state': 'draft'})
        else:
            return super(AccountPayment, self).action_draft()
    
    def action_cancel(self):
        """Cancelar"""
        if self.is_multi and self.method_line_ids:
            self.write({'state': 'cancelled'})
        else:
            return super(AccountPayment, self).action_cancel()

    def button_canceled(self):
        """Cancelar"""
        self.write({'state': 'cancelled'})