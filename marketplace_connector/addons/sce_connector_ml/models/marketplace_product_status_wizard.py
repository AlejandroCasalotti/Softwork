# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class MarketplaceProductStatusWizard(models.TransientModel):
    _name = "marketplace.product.status.wizard"
    _description = "Wizard de Estado y Conciliación de Productos Marketplace"

    account_id = fields.Many2one("sce.account", string="Cuenta Marketplace", required=True, readonly=True)
    total_ml_items = fields.Integer(string="Total Publicaciones en Mercado Libre", readonly=True)
    total_sce_publications = fields.Integer(string="Total Publicaciones en SCE / Odoo", readonly=True)
    reconciled_count = fields.Integer(string="Productos Conciliados / Vinculados", readonly=True)
    unreconciled_ml_count = fields.Integer(string="Publicaciones ML Sin Vincular", readonly=True)
    reconciliation_rate = fields.Float(string="Porcentaje de Conciliación (%)", readonly=True)

    status_state = fields.Selection(
        selection=[
            ("full", "🟢 100% Conciliados"),
            ("partial", "🟡 Conciliación Parcial"),
            ("none", "🔴 Sin Conciliar"),
        ],
        string="Estado de Conciliación",
        readonly=True,
    )
    summary_message = fields.Text(string="Diagnóstico de Estado", readonly=True)
    recommendation_notes = fields.Text(string="Recomendación / Siguiente Paso", readonly=True)

    def action_open_publications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Publicaciones de {self.account_id.display_name}",
            "res_model": "marketplace.publication",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.account_id.id)],
            "target": "current",
        }

    def action_sync_from_ml(self):
        self.ensure_one()
        # Encola job de sincronizacion de productos
        job = self.env["sce.job"].create({
            "name": f"Sincronizar publicaciones - {self.account_id.display_name}",
            "account_id": self.account_id.id,
            "job_type": "sync_products",
            "payload_json": "{}",
        })
        job.action_enqueue()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sincronización Iniciada",
                "message": f"Se ha encolado el trabajo de sincronización para {self.account_id.display_name}. Se conciliarán las publicaciones automáticamente.",
                "type": "success",
                "sticky": False,
            },
        }
