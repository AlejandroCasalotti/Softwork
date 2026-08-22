# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Marketplace Account
"""


from __future__ import annotations


from odoo import (
    api,
    fields,
    models,
)



class SCEAccount(models.Model):

    """
    External marketplace account.

    Represents a connected external
    marketplace account handled by SCE.
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

        tracking=True,

        index=True,

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

        index=True,

    )



    # -------------------------------------------------------------------------
    # External Identity
    # -------------------------------------------------------------------------

    external_user_id = fields.Char(

        string="External User ID",

        tracking=True,

        index=True,

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

            ("connecting", "Connecting"),

            ("connected", "Connected"),

            ("expired", "Expired"),

            ("error", "Error"),

            ("disabled", "Disabled"),

        ],

        string="Status",

        default="draft",

        required=True,

        tracking=True,

    )



    connected = fields.Boolean(

        string="Connected",

        compute="_compute_connected",

        store=True,

    )



    last_connection = fields.Datetime(

        readonly=True,

    )



    last_sync = fields.Datetime(

        readonly=True,

    )



    last_error_date = fields.Datetime(

        readonly=True,

    )



    last_error_message = fields.Text(

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

            ("token", "Access Token"),

            ("basic", "Basic Authentication"),

            ("credentials", "Username / Password"),

        ],

        string="Authentication Type",

        default="oauth2",

    )



    # -------------------------------------------------------------------------
    # OAuth Application
    # -------------------------------------------------------------------------

    client_id = fields.Char(

        string="Client ID",

    )


    client_secret = fields.Char(

        string="Client Secret",

        copy=False,

    )


    redirect_uri = fields.Char(

        string="Redirect URI",

    )



    # -------------------------------------------------------------------------
    # User Credentials
    # -------------------------------------------------------------------------

    username = fields.Char(

        string="Username",

    )


    password = fields.Char(

        string="Password",

        copy=False,

    )



    # -------------------------------------------------------------------------
    # Tokens
    # -------------------------------------------------------------------------

    access_token = fields.Char(

        string="Access Token",

        copy=False,

    )


    refresh_token_value = fields.Char(

        string="Refresh Token",

        copy=False,

    )


    token_expiration = fields.Datetime(

        string="Token Expiration",

    )


    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    job_count = fields.Integer(

        string="Jobs",

        compute="_compute_statistics",

    )


    queue_count = fields.Integer(

        string="Queue Items",

        compute="_compute_statistics",

    )


    log_count = fields.Integer(

        string="Logs",

        compute="_compute_statistics",

    )


    webhook_count = fields.Integer(

        string="Webhooks",

        compute="_compute_statistics",

    )


    # -------------------------------------------------------------------------
    # Compute Statistics
    # -------------------------------------------------------------------------

    @api.depends(
        "connector_id",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]

        Queue = self.env["sce.queue"]

        Log = self.env["sce.log"]

        Webhook = self.env["sce.webhook"]


        for account in self:


            account.job_count = Job.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.queue_count = Queue.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.log_count = Log.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.webhook_count = Webhook.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.error_count = Log.search_count(

                [

                    (
                        "account_id",
                        "=",
                        account.id,
                    ),

                    (
                        "level",
                        "in",
                        [
                            "error",
                            "critical",
                        ],
                    ),

                ]

            )



    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def action_connect(self):

        self.ensure_one()


        self.write({

            "state":
                "connecting",

        })


        try:

            provider = self.get_provider()


            result = provider.connect(
                self
            )


            self.write({

                "state":
                    "connected",

                "last_connection":
                    fields.Datetime.now(),

                "last_error_date":
                    False,

                "last_error_message":
                    False,

            })


            self._log_info(
                "Account connected successfully."
            )


            return result



        except Exception as error:


            self.write({

                "state":
                    "error",

                "last_error_date":
                    fields.Datetime.now(),

                "last_error_message":
                    str(error),

            })


            self._log_error(
                error
            )


            raise



    # -------------------------------------------------------------------------

    def action_disconnect(self):

        self.ensure_one()


        try:


            provider = self.get_provider()


            result = provider.disconnect(
                self
            )


            self.write({

                "state":
                    "disabled",

            })


            self._log_info(
                "Account disconnected."
            )


            return result



        except Exception as error:


            self.write({

                "state":
                    "error",

                "last_error_date":
                    fields.Datetime.now(),

                "last_error_message":
                    str(error),

            })


            self._log_error(
                error
            )


            raise



    # -------------------------------------------------------------------------

    def action_test_connection(self):

        self.ensure_one()


        provider = self.get_provider()


        result = provider.test_connection(
            self
        )


        self._log_info(
            "Connection test executed."
        )


        return result



    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    def action_synchronize(self):

        self.ensure_one()


        job = self.env[
            "sce.job"
        ].create({

            "type":
                "synchronize_all",

            "account_id":
                self.id,

            "priority":
                "2",

            "payload":
                {

                    "account_id":
                        self.id,

                },

        })


        queue = self.env[
            "sce.queue"
        ].create({

            "action":
                "synchronize_all",

            "account_id":
                self.id,

            "job_id":
                job.id,

            "priority":
                "2",

            "payload":
                {

                    "account_id":
                        self.id,

                },

        })


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

    def action_refresh_token(self):

        self.ensure_one()


        provider = self.get_provider()


        result = provider.refresh_token(
            self
        )


        self.write({

            "last_connection":
                fields.Datetime.now(),

        })


        return result



    # -------------------------------------------------------------------------
    # Provider Access
    # -------------------------------------------------------------------------

    def get_provider(self):

        self.ensure_one()


        kernel = self.env[
            "sce.kernel"
        ]


        return kernel.get_provider(
            self.connector_code
        )



    # -------------------------------------------------------------------------
    # Credentials
    # -------------------------------------------------------------------------

    def get_credentials(self):

        self.ensure_one()


        return {

            "auth_type":
                self.auth_type,


            "client_id":
                self.client_id,


            "client_secret":
                self.client_secret,


            "username":
                self.username,


            "password":
                self.password,


            "access_token":
                self.access_token,


            "refresh_token":
                self.refresh_token,


            "token_expiration":
                self.token_expiration,


        }



    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def get_configuration(
        self,
        key=None,
    ):

        self.ensure_one()


        configuration = self.configuration or {}


        if key:

            return configuration.get(
                key
            )


        return configuration


    # -------------------------------------------------------------------------
    # Compute Statistics
    # -------------------------------------------------------------------------

    @api.depends(
        "connector_id",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]

        Queue = self.env["sce.queue"]

        Log = self.env["sce.log"]

        Webhook = self.env["sce.webhook"]


        for account in self:


            account.job_count = Job.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.queue_count = Queue.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.log_count = Log.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.webhook_count = Webhook.search_count(
                [
                    (
                        "account_id",
                        "=",
                        account.id,
                    )
                ]
            )


            account.error_count = Log.search_count(

                [

                    (
                        "account_id",
                        "=",
                        account.id,
                    ),

                    (
                        "level",
                        "in",
                        [
                            "error",
                            "critical",
                        ],
                    ),

                ]

            )



    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def action_connect(self):

        self.ensure_one()


        self.write({

            "state":
                "connecting",

        })


        try:

            provider = self.get_provider()


            result = provider.connect(
                self
            )


            self.write({

                "state":
                    "connected",

                "last_connection":
                    fields.Datetime.now(),

                "last_error_date":
                    False,

                "last_error_message":
                    False,

            })


            self._log_info(
                "Account connected successfully."
            )


            return result



        except Exception as error:


            self.write({

                "state":
                    "error",

                "last_error_date":
                    fields.Datetime.now(),

                "last_error_message":
                    str(error),

            })


            self._log_error(
                error
            )


            raise



    # -------------------------------------------------------------------------

    def action_disconnect(self):

        self.ensure_one()


        try:


            provider = self.get_provider()


            result = provider.disconnect(
                self
            )


            self.write({

                "state":
                    "disabled",

            })


            self._log_info(
                "Account disconnected."
            )


            return result



        except Exception as error:


            self.write({

                "state":
                    "error",

                "last_error_date":
                    fields.Datetime.now(),

                "last_error_message":
                    str(error),

            })


            self._log_error(
                error
            )


            raise



    # -------------------------------------------------------------------------

    def action_test_connection(self):

        self.ensure_one()


        provider = self.get_provider()


        result = provider.test_connection(
            self
        )


        self._log_info(
            "Connection test executed."
        )


        return result



    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    def action_synchronize(self):

        self.ensure_one()


        job = self.env[
            "sce.job"
        ].create({

            "type":
                "synchronize_all",

            "account_id":
                self.id,

            "priority":
                "2",

            "payload":
                {

                    "account_id":
                        self.id,

                },

        })


        queue = self.env[
            "sce.queue"
        ].create({

            "action":
                "synchronize_all",

            "account_id":
                self.id,

            "job_id":
                job.id,

            "priority":
                "2",

            "payload":
                {

                    "account_id":
                        self.id,

                },

        })


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

    def action_refresh_token(self):

        self.ensure_one()


        provider = self.get_provider()


        result = provider.refresh_token(
            self
        )


        self.write({

            "last_connection":
                fields.Datetime.now(),

        })


        return result



    # -------------------------------------------------------------------------
    # Provider Access
    # -------------------------------------------------------------------------

    def get_provider(self):

        self.ensure_one()


        kernel = self.env[
            "sce.kernel"
        ]


        return kernel.get_provider(
            self.connector_code
        )



    # -------------------------------------------------------------------------
    # Credentials
    # -------------------------------------------------------------------------

    def get_credentials(self):

        self.ensure_one()


        return {

            "auth_type":
                self.auth_type,


            "client_id":
                self.client_id,


            "client_secret":
                self.client_secret,


            "username":
                self.username,


            "password":
                self.password,


            "access_token":
                self.access_token,


            "refresh_token":
                self.refresh_token,


            "token_expiration":
                self.token_expiration,


        }



    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def get_configuration(
        self,
        key=None,
    ):

        self.ensure_one()


        configuration = self.configuration or {}


        if key:

            return configuration.get(
                key
            )


        return configuration