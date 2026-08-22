# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Mercado Libre Account.
"""

from __future__ import annotations

from odoo import fields, models


class MLAccount(models.Model):
    _name = "sce.ml.account"
    _description = "Mercado Libre Account"
    _order = "id"

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_id = fields.Many2one(
        comodel_name="sce.account",
        string="SCE Account",
        required=True,
        ondelete="cascade",
        index=True,
    )

    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        readonly=True,
    )

    site_id = fields.Many2one(
        comodel_name="sce.ml.site",
        string="Marketplace Site",
        required=True,
        ondelete="restrict",
    )

    # -------------------------------------------------------------------------
    # OAuth Configuration
    # -------------------------------------------------------------------------

    client_id = fields.Char(
        string="Client ID",
        required=True,
    )

    client_secret = fields.Char(
        string="Client Secret",
        required=True,
        password=True,
    )

    redirect_uri = fields.Char(
        string="Redirect URI",
        required=True,
    )

    oauth_state = fields.Char(
        string="OAuth State",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # Seller Information
    # -------------------------------------------------------------------------

    seller_id = fields.Char(
        string="Seller ID",
        readonly=True,
    )

    seller_nickname = fields.Char(
        string="Seller Nickname",
        readonly=True,
    )

    user_id = fields.Char(
        string="Mercado Libre User ID",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    connected = fields.Boolean(
        string="Connected",
        default=False,
        readonly=True,
    )

    last_sync_at = fields.Datetime(
        string="Last Synchronization",
        readonly=True,
    )

    last_sync_status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        string="Last Status",
        readonly=True,
    )

    last_error = fields.Text(
        string="Last Error",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Options
    # -------------------------------------------------------------------------

    auto_import_orders = fields.Boolean(
        string="Import Orders",
        default=True,
    )

    auto_update_stock = fields.Boolean(
        string="Update Stock",
        default=True,
    )

    auto_update_price = fields.Boolean(
        string="Update Prices",
        default=True,
    )

    webhook_secret = fields.Char(
        string="Webhook Secret",
    )

    active = fields.Boolean(
        default=True,
    )

    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _account_unique = models.Constraint(
        "UNIQUE(account_id)",
        "Each SCE Account can only have one Mercado Libre configuration.",
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def mark_connected(self):
        """
        Marks the account as connected.
        """
        self.ensure_one()
        self.write({
            "connected": True,
        })

    def mark_disconnected(self):
        """
        Marks the account as disconnected.
        """
        self.ensure_one()
        self.write({
            "connected": False,
        })