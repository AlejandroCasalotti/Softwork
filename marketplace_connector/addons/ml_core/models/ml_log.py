# -*- coding: utf-8 -*-
from odoo import fields, models


class MlLog(models.Model):
    _name = "ml.log"
    _description = "Log MercadoLibre"
    _order = "create_date desc"

    account_id = fields.Many2one("ml.account", string="Cuenta", ondelete="set null")
    level = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("error", "Error")],
        default="info",
        required=True,
    )
    message = fields.Char(required=True)
    detail = fields.Text()