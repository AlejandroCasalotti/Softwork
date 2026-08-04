# -*- coding: utf-8 -*-
from odoo import fields, models


class SceIntegrationStatusSnapshot(models.Model):
    _name = "sce.integration.status.snapshot"
    _description = "Snapshot de Diagnóstico de Integración"
    _order = "create_date desc"

    name = fields.Char(default="Diagnóstico", required=True)
    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="account_id.company_id", store=True, readonly=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    executed_at = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)

    health_score = fields.Integer()
    ok_count = fields.Integer()
    warning_count = fields.Integer()
    error_count = fields.Integer()

    line_ids = fields.One2many(
        "sce.integration.status.snapshot.line",
        "snapshot_id",
        string="Resultados",
    )


class SceIntegrationStatusSnapshotLine(models.Model):
    _name = "sce.integration.status.snapshot.line"
    _description = "Línea Snapshot Diagnóstico"
    _order = "id"

    snapshot_id = fields.Many2one(
        "sce.integration.status.snapshot",
        required=True,
        ondelete="cascade",
        index=True,
    )
    test_name = fields.Char(required=True)
    status = fields.Selection(
        [("success", "Success"), ("warning", "Warning"), ("error", "Error")],
        required=True,
        default="warning",
    )
    message = fields.Char()
    error_details = fields.Text()
    action_type = fields.Selection(
        [
            ("none", "Ninguna"),
            ("reconnect", "Reconectar"),
            ("open_warehouse", "Abrir almacenes"),
            ("open_pricelist", "Abrir listas de precios"),
            ("open_locations", "Abrir ubicaciones"),
            ("open_settings", "Abrir ajustes"),
        ],
        default="none",
    )