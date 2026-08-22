# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Credential Store

This model stores authentication credentials used by
Marketplace Providers.

It is intentionally generic and independent from any
specific authentication mechanism (OAuth2, API Key,
Basic Auth, JWT, AWS Keys, etc.).
"""

from __future__ import annotations

from odoo import api, fields, models


class SCECredential(models.Model):
    _name = "sce.credential"
    _description = "SCE Credential"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        required=True,
        tracking=True,
    )

    active = fields.Boolean(
        default=True,
    )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    account_id = fields.Many2one(
        "sce.account",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # -------------------------------------------------------------------------
    # Credential
    # -------------------------------------------------------------------------

    credential_type = fields.Selection(
        [
            ("oauth2", "OAuth2"),
            ("api_key", "API Key"),
            ("basic", "Basic Authentication"),
            ("bearer", "Bearer Token"),
            ("jwt", "JWT"),
            ("custom", "Custom"),
        ],
        required=True,
        default="oauth2",
        tracking=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("valid", "Valid"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
            ("invalid", "Invalid"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    version = fields.Integer(
        default=1,
        required=True,
    )

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------

    data = fields.Json(
        string="Credential Data",
        default=dict,
    )

    metadata = fields.Json(
        string="Metadata",
        default=dict,
    )

    expires_at = fields.Datetime()

    last_validation = fields.Datetime()

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------

    is_expired = fields.Boolean(
        compute="_compute_is_expired",
        store=True,
    )

    @api.depends("expires_at")
    def _compute_is_expired(self):
        now = fields.Datetime.now()

        for credential in self:
            credential.is_expired = bool(
                credential.expires_at
                and credential.expires_at <= now
            )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_validate(self):
        self.ensure_one()
        return self.env["sce.credential.service"].validate(self)

    def action_refresh(self):
        self.ensure_one()
        return self.env["sce.credential.service"].refresh(self)

    def action_revoke(self):
        self.ensure_one()
        return self.env["sce.credential.service"].revoke(self)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    _version_positive = models.Constraint(
        "CHECK(version > 0)",
        "Credential version must be greater than zero.",
    )