# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Marketplace Account
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEAccount(models.Model):
    """
    Marketplace account configuration.

    Represents a real external marketplace account.
    """

    _name = "sce.account"

    _description = "SCE Marketplace Account"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = "name"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Account Name",
        required=True,
        tracking=True,
    )


    active = fields.Boolean(
        default=True,
    )


    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )


    # -------------------------------------------------------------------------
    # Connector
    # -------------------------------------------------------------------------

    connector_id = fields.Many2one(
        "sce.connector",
        string="Connector",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )


    connector_code = fields.Char(
        related="connector_id.code",
        store=True,
        readonly=True,
        index=True,
    )


    plugin_id = fields.Many2one(
        related="connector_id.plugin_id",
        store=True,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # External Identity
    # -------------------------------------------------------------------------

    external_user_id = fields.Char(
        string="External User ID",
        tracking=True,
    )


    external_user_name = fields.Char(
        string="External Username",
        tracking=True,
    )


    external_email = fields.Char(
        string="External Email",
    )


    # -------------------------------------------------------------------------
    # Connection State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("connected", "Connected"),
            ("error", "Error"),
            ("disabled", "Disabled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )


    connected = fields.Boolean(
        compute="_compute_connected",
        store=True,
    )


    last_connection = fields.Datetime(
        readonly=True,
    )


    last_sync = fields.Datetime(
        readonly=True,
    )

        # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    auth_type = fields.Selection(
        [
            ("none", "None"),
            ("oauth2", "OAuth 2.0"),
            ("api_key", "API Key"),
            ("basic", "Basic Authentication"),
            ("token", "Access Token"),
        ],
        string="Authentication Type",
        default="oauth2",
    )


    client_id = fields.Char(
        string="Client ID",
    )


    client_secret = fields.Char(
        string="Client Secret",
        password=True,
    )


    access_token = fields.Char(
        string="Access Token",
        password=True,
        copy=False,
    )


    refresh_token = fields.Char(
        string="Refresh Token",
        password=True,
        copy=False,
    )


    token_expiration = fields.Datetime(
        string="Token Expiration",
    )


    # -------------------------------------------------------------------------
    # Connection Configuration
    # -------------------------------------------------------------------------

    redirect_uri = fields.Char(
        string="Redirect URI",
    )


    api_url = fields.Char(
        string="API URL",
    )


    sandbox = fields.Boolean(
        string="Sandbox Mode",
        default=False,
    )


    configuration = fields.Json(
        string="Configuration",
        default=dict,
    )


    # -------------------------------------------------------------------------
    # Synchronization Settings
    # -------------------------------------------------------------------------

    auto_sync = fields.Boolean(
        string="Automatic Synchronization",
        default=True,
    )


    sync_interval = fields.Integer(
        string="Synchronization Interval (minutes)",
        default=15,
    )


    sync_products = fields.Boolean(
        string="Sync Products",
        default=True,
    )


    sync_orders = fields.Boolean(
        string="Sync Orders",
        default=True,
    )


    sync_stock = fields.Boolean(
        string="Sync Stock",
        default=True,
    )


    sync_prices = fields.Boolean(
        string="Sync Prices",
        default=True,
    )


    sync_shipments = fields.Boolean(
        string="Sync Shipments",
        default=True,
    )

        # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    job_ids = fields.One2many(
        "sce.job",
        "account_id",
        string="Jobs",
    )


    queue_ids = fields.One2many(
        "sce.queue",
        "account_id",
        string="Queue Items",
    )


    log_ids = fields.One2many(
        "sce.log",
        "account_id",
        string="Logs",
    )


    webhook_ids = fields.One2many(
        "sce.webhook",
        "account_id",
        string="Webhooks",
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends("state")
    def _compute_connected(self):
         for account in self:
        account.connected = account.state == "connected"


    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    job_count = fields.Integer(
        compute="_compute_statistics",
    )


    queue_count = fields.Integer(
        compute="_compute_statistics",
    )


    log_count = fields.Integer(
        compute="_compute_statistics",
    )


    webhook_count = fields.Integer(
        compute="_compute_statistics",
    )


    error_count = fields.Integer(
        compute="_compute_statistics",
    )


    # -------------------------------------------------------------------------
    # Synchronization Statistics
    # -------------------------------------------------------------------------

    products_synced = fields.Integer(
        default=0,
        readonly=True,
    )


    orders_synced = fields.Integer(
        default=0,
        readonly=True,
    )


    shipments_synced = fields.Integer(
        default=0,
        readonly=True,
    )


    last_sync_status = fields.Selection(
        [
            ("success", "Success"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        readonly=True,
    )


    last_sync_message = fields.Text(
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "job_ids",
        "queue_ids",
        "log_ids",
        "webhook_ids",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]

        Queue = self.env["sce.queue"]

        Log = self.env["sce.log"]

        Webhook = self.env["sce.webhook"]


        for account in self:


            account.job_count = (
                Job.search_count(
                    [
                        (
                            "account_id",
                            "=",
                            account.id,
                        )
                    ]
                )
            )


            account.queue_count = (
                Queue.search_count(
                    [
                        (
                            "account_id",
                            "=",
                            account.id,
                        )
                    ]
                )
            )


            account.log_count = (
                Log.search_count(
                    [
                        (
                            "account_id",
                            "=",
                            account.id,
                        )
                    ]
                )
            )


            account.webhook_count = (
                Webhook.search_count(
                    [
                        (
                            "account_id",
                            "=",
                            account.id,
                        )
                    ]
                )
            )


            account.error_count = (
                Log.search_count(
                    [
                        (
                            "account_id",
                            "=",
                            account.id,
                        ),
                        (
                            "level",
                            "=",
                            "error",
                        ),
                    ]
                )
            )

                # -------------------------------------------------------------------------
    # Connection Actions
    # -------------------------------------------------------------------------

    def action_connect(self):

        self.ensure_one()

        provider = (
            self.plugin_id.provider()
        )

        result = provider.connect(
            self
        )


        self.write({

            "state":
                "connected",

            "last_connection":
                fields.Datetime.now(),

        })


        return result



    # -------------------------------------------------------------------------

    def action_disconnect(self):

        self.ensure_one()

        provider = (
            self.plugin_id.provider()
        )


        result = provider.disconnect(
            self
        )


        self.write({

            "state":
                "disabled",

        })


        return result



    # -------------------------------------------------------------------------

    def action_test_connection(self):

        self.ensure_one()

        provider = (
            self.plugin_id.provider()
        )


        return provider.test_connection(
            self
        )



    # -------------------------------------------------------------------------
    # Synchronization Actions
    # -------------------------------------------------------------------------

    def action_synchronize(self):

        self.ensure_one()

        kernel = self.env[
            "sce.kernel"
        ]


        job = kernel.create_job(

            self,

            "synchronize_all",

        )


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Synchronization Job",

            "res_model":
                "sce.job",

            "view_mode":
                "form",

            "res_id":
                job.id,

        }



    # -------------------------------------------------------------------------
    # Token Management
    # -------------------------------------------------------------------------

    def refresh_token(self):

        self.ensure_one()

        provider = (
            self.plugin_id.provider()
        )


        result = provider.refresh_token(
            self
        )


        return result



    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_provider(self):

        self.ensure_one()

        return (
            self.plugin_id.provider()
        )



    # -------------------------------------------------------------------------

    def get_configuration(
        self,
        key=None,
    ):
        """
        Returns account configuration.
        """

        self.ensure_one()


        configuration = (
            self.configuration or {}
        )


        if key:

            return configuration.get(
                key
            )


        return configuration



    # -------------------------------------------------------------------------

    def update_sync_status(
        self,
        status,
        message=None,
    ):

        self.ensure_one()


        values = {

            "last_sync_status":
                status,

            "last_sync_message":
                message,

            "last_sync":
                fields.Datetime.now(),

        }


        self.write(
            values
        )



    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(
        self,
        vals_list,
    ):

        records = super().create(
            vals_list
        )


        for account in records:

            if not account.name:

                account.name = (
                    account.connector_id.name
                )


        return records



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (
            "sce_account_name_connector_unique",

            "unique(company_id, connector_id, name)",

            "Account name must be unique per connector.",

        ),

    ]