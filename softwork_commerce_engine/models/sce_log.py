# -*- coding: utf-8 -*-
from odoo import fields, models


class SceLog(models.Model):
    _name = "sce.log"
    _description = "SCE Technical Log"
    _order = "create_date desc"

    name = fields.Char(required=True)
    level = fields.Selection(
        selection=[
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARNING", "WARNING"),
            ("ERROR", "ERROR"),
            ("CRITICAL", "CRITICAL"),
        ],
        default="INFO",
        required=True,
        index=True,
    )
    connector_id = fields.Many2one("sce.connector", ondelete="set null", index=True)
    account_id = fields.Many2one("sce.account", ondelete="set null", index=True)
    job_id = fields.Many2one("sce.job", ondelete="set null", index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    message = fields.Text(required=True)
    details_json = fields.Text()