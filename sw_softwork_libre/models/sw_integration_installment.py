# -*- coding: utf-8 -*-
from odoo import fields, models


class SwIntegrationInstallment(models.Model):
    _name = "sw.integration.installment"
    _description = "Recargo por Cuotas MercadoLibre"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    integration_id = fields.Many2one("sw.integration", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    meli_installments = fields.Integer(string="Cuotas")
    surcharge_percent = fields.Float(string="Recargo %", default=0.0)