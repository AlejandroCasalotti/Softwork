# -*- coding: utf-8 -*-
import base64
import csv
from io import StringIO

from odoo import api, fields, models


class SceIntegrationStatusWizard(models.TransientModel):
    _name = "sce.integration.status.wizard"
    _description = "Wizard de Estado de Integración"

    account_id = fields.Many2one("sce.account", string="Cuenta", required=True, readonly=True)
    title = fields.Char(string="Título", readonly=True, default="Resultado del análisis de su integración")
    subtitle = fields.Text(
        string="Subtítulo",
        readonly=True,
        default=(
            "Resultado del Chequeo de estado de tu Integración\n"
            "A continuación se muestran los resultados de diferentes pruebas de conectividad y "
            "configuración realizadas en su integración."
        ),
    )
    test_line_ids = fields.One2many(
        "sce.integration.status.wizard.line",
        "wizard_id",
        string="Resultados de tests",
    )

    ok_count = fields.Integer(string="OK", compute="_compute_summary", store=False)
    warning_count = fields.Integer(string="Warnings", compute="_compute_summary", store=False)
    error_count = fields.Integer(string="Errores", compute="_compute_summary", store=False)
    health_score = fields.Integer(string="Health Score", compute="_compute_summary", store=False)

    @api.depends("test_line_ids.status")
    def _compute_summary(self):
        for rec in self:
            ok = len(rec.test_line_ids.filtered(lambda l: l.status == "success"))
            warn = len(rec.test_line_ids.filtered(lambda l: l.status == "warning"))
            err = len(rec.test_line_ids.filtered(lambda l: l.status == "error"))
            total = ok + warn + err
            score = 100
            if total:
                score = max(0, min(100, int(((ok * 1.0) + (warn * 0.5)) / total * 100)))
            rec.ok_count = ok
            rec.warning_count = warn
            rec.error_count = err
            rec.health_score = score

    def action_rerun_diagnostic(self):
        self.ensure_one()
        vals_list = self.account_id._run_integration_status_tests()
        self.account_id._create_status_snapshot(vals_list)
        self.write({"test_line_ids": [(5, 0, 0)] + [(0, 0, vals) for vals in vals_list]})
        return {
            "type": "ir.actions.act_window",
            "name": "Verificar Estado de Integración",
            "res_model": "sce.integration.status.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_export_csv(self):
        self.ensure_one()
        output = StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Test", "Estado", "Resultado", "Detalle", "Accion"])
        for line in self.test_line_ids:
            writer.writerow([
                line.test_name or "",
                line.status or "",
                line.message or "",
                line.error_details or "",
                line.action_type or "",
            ])

        csv_data = output.getvalue().encode("utf-8")
        attachment = self.env["ir.attachment"].create({
            "name": f"diagnostico_integracion_{self.id}.csv",
            "type": "binary",
            "datas": base64.b64encode(csv_data),
            "mimetype": "text/csv",
            "res_model": self._name,
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


class SceIntegrationStatusWizardLine(models.TransientModel):
    _name = "sce.integration.status.wizard.line"
    _description = "Linea de Test de Estado de Integración"

    wizard_id = fields.Many2one(
        "sce.integration.status.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    test_name = fields.Char(string="Test", required=True)
    status = fields.Selection(
        [("success", "Success"), ("warning", "Warning"), ("error", "Error")],
        string="Estado",
        required=True,
        default="warning",
    )
    message = fields.Char(string="Resultado")
    error_details = fields.Text(string="Detalle de Errores")
    action_type = fields.Selection(
        [
            ("none", "Ninguna"),
            ("reconnect", "Reconectar"),
            ("open_warehouse", "Abrir almacenes"),
            ("open_pricelist", "Abrir listas de precios"),
            ("open_locations", "Abrir ubicaciones"),
            ("open_settings", "Abrir ajustes"),
        ],
        string="Acción",
        default="none",
    )

    def action_execute_quick_fix(self):
        self.ensure_one()
        account = self.wizard_id.account_id
        if self.action_type == "reconnect":
            return account.action_open_oauth_url()
        if self.action_type == "open_warehouse":
            return {
                "type": "ir.actions.act_window",
                "name": "Almacenes",
                "res_model": "stock.warehouse",
                "view_mode": "list,form",
                "target": "current",
            }
        if self.action_type == "open_pricelist":
            return {
                "type": "ir.actions.act_window",
                "name": "Listas de Precios",
                "res_model": "product.pricelist",
                "view_mode": "list,form",
                "target": "current",
            }
        if self.action_type == "open_locations":
            return {
                "type": "ir.actions.act_window",
                "name": "Ubicaciones",
                "res_model": "stock.location",
                "view_mode": "list,form",
                "target": "current",
            }
        if self.action_type == "open_settings":
            return {
                "type": "ir.actions.act_window",
                "name": "Parámetros del sistema",
                "res_model": "ir.config_parameter",
                "view_mode": "list,form",
                "target": "current",
            }
        return {"type": "ir.actions.act_window_close"}