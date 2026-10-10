# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceInstallmentRule(models.Model):
    _name = "marketplace.installment.rule"
    _description = "Regla de recargo por cuotas de la cuenta de marketplace"
    _order = "sequence, id"

    account_id = fields.Many2one(
        "sce.account", string="Cuenta", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Nombre", required=True)
    installments_qty = fields.Integer(
        string="Cantidad de Cuotas",
        default=0,
        help="Cantidad de cuotas que reporta Mercado Libre para esta regla. Dejar en 0 si la regla aplica a cualquier cantidad (ver 'Aplica a cualquier cantidad').",
    )
    no_interest = fields.Boolean(
        string="Cuotas Sin Interés",
        default=True,
        help="Marcado si esta regla corresponde a cuotas 'al mismo precio que publicaste' (sin interés para el comprador). Desmarcado para cuotas con interés.",
    )
    applies_to_any_qty = fields.Boolean(
        string="Aplica a cualquier cantidad de cuotas",
        default=False,
        help="Si se marca, la regla aplica sin importar la cantidad exacta de cuotas que informe Mercado Libre (útil para el caso 'con interés').",
    )
    surcharge_percent = fields.Float(string="Recargo (%)", default=0.0)
