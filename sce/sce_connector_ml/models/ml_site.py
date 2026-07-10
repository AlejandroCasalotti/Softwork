# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Mercado Libre Site Model.
"""

from odoo import api, fields, models


class MLSite(models.Model):
    _name = "sce.ml.site"
    _description = "Mercado Libre Site"
    _rec_name = "display_name"
    _order = "code"

    # -------------------------------------------------------------------------
    # Basic Information
    # -------------------------------------------------------------------------

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
    )

    name = fields.Char(
        string="Country",
        required=True,
        translate=True,
    )

    country_code = fields.Char(
        string="Country Code",
        required=True,
        size=2,
    )

    language_code = fields.Char(
        string="Language Code",
        required=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        ondelete="restrict",
    )

    timezone = fields.Char(
        string="Timezone",
        default="UTC",
    )

    api_base_url = fields.Char(
        string="API Base URL",
        required=True,
        default="https://api.mercadolibre.com",
    )

    auth_base_url = fields.Char(
        string="OAuth Base URL",
        required=True,
        default="https://auth.mercadolibre.com",
    )

    active = fields.Boolean(
        default=True,
    )

    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [
        (
            "sce_ml_site_code_unique",
            "unique(code)",
            "The site code must be unique.",
        ),
    ]

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_api_url(self):
        """
        Returns the API base URL.
        """
        self.ensure_one()
        return self.api_base_url

    def get_auth_url(self):
        """
        Returns the OAuth base URL.
        """
        self.ensure_one()
        return self.auth_base_url