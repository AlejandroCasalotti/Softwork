# -*- coding: utf-8 -*-
from odoo import fields, models


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
        readonly=True,
    )


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