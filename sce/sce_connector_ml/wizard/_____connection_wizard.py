# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Connection Wizard

Universal marketplace connection wizard.

This wizard is intentionally generic so it can be
reused by every SCE connector.
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEConnectionWizard(models.TransientModel):
    """
    Universal connection assistant.

    Handles the complete lifecycle of connecting
    a marketplace account to SCE.
    """

    _name = "sce.connection.wizard"

    _description = "SCE Connection Wizard"



    # ============================================================
    # Wizard Information
    # ============================================================

    state = fields.Selection(
        [
            ("draft", "Welcome"),
            ("configuration", "Configuration"),
            ("authorization", "Authorization"),
            ("connecting", "Connecting"),
            ("validating", "Validation"),
            ("finished", "Finished"),
            ("error", "Error"),
        ],
        default="draft",
        readonly=True,
    )


    progress = fields.Integer(
        string="Progress",
        default=0,
        readonly=True,
    )


    message = fields.Text(
        string="Current Status",
        readonly=True,
    )


    error_message = fields.Text(
        string="Error",
        readonly=True,
    )



    # ============================================================
    # Connector
    # ============================================================

    connector_id = fields.Many2one(
        "sce.connector",
        string="Marketplace",
        required=True,
    )


    plugin_id = fields.Many2one(
        related="connector_id.plugin_id",
        readonly=True,
    )



    # ============================================================
    # Company
    # ============================================================

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )



    # ============================================================
    # Account
    # ============================================================

    account_id = fields.Many2one(
        "sce.account",
        string="Marketplace Account",
    )


    create_new_account = fields.Boolean(
        default=True,
    )


    account_name = fields.Char(
        string="Account Name",
    )



    # ============================================================
    # OAuth
    # ============================================================

    authorization_url = fields.Char(
        readonly=True,
    )


    authorization_code = fields.Char(
        readonly=True,
    )



    # ============================================================
    # User Information
    # ============================================================

    external_user_id = fields.Char(
        readonly=True,
    )


    external_username = fields.Char(
        readonly=True,
    )


    external_email = fields.Char(
        readonly=True,
    )



    # ============================================================
    # Marketplace Information
    # ============================================================

    marketplace_name = fields.Char(
        readonly=True,
    )


    marketplace_country = fields.Char(
        readonly=True,
    )


    marketplace_currency = fields.Char(
        readonly=True,
    )



    # ============================================================
    # Connection Results
    # ============================================================

    token_received = fields.Boolean(
        readonly=True,
    )


    connection_success = fields.Boolean(
        readonly=True,
    )


    validation_success = fields.Boolean(
        readonly=True,
    )



    # ============================================================
    # Computed
    # ============================================================

    can_continue = fields.Boolean(
        compute="_compute_can_continue",
    )


    can_finish = fields.Boolean(
        compute="_compute_can_finish",
    )



    # ============================================================
    # Compute
    # ============================================================

    @api.depends(
        "connector_id",
        "company_id",
    )
    def _compute_can_continue(self):

        for wizard in self:

            wizard.can_continue = bool(
                wizard.connector_id
            )


    @api.depends(
        "connection_success",
        "validation_success",
    )
    def _compute_can_finish(self):

        for wizard in self:

            wizard.can_finish = (

                wizard.connection_success

                and

                wizard.validation_success

            )



    # ============================================================
    # Defaults
    # ============================================================

    @api.model
    def default_get(
        self,
        fields_list,
    ):

        values = super().default_get(
            fields_list
        )

        connector = self.env[
            "sce.connector"
        ].search(
            [
                (
                    "active",
                    "=",
                    True,
                )
            ],
            limit=1,
        )

        if connector:

            values.setdefault(
                "connector_id",
                connector.id,
            )

        return values



    # ============================================================
    # Helpers
    # ============================================================

    def _kernel(self):

        return self.env[
            "sce.kernel"
        ]


    def _provider(self):

        self.ensure_one()

        return self.plugin_id.provider()


    def _update_progress(
        self,
        progress,
        message,
    ):

        self.write({

            "progress": progress,

            "message": message,

        })


    def _set_error(
        self,
        message,
    ):

        self.write({

            "state": "error",

            "error_message": message,

        })


    def _reset(self):

        self.write({

            "state": "draft",

            "progress": 0,

            "message": False,

            "error_message": False,

            "token_received": False,

            "connection_success": False,

            "validation_success": False,

        })

    # ============================================================
    # Wizard Flow
    # ============================================================

    def action_start(self):
        """
        Starts the connection wizard.
        """

        self.ensure_one()

        self._update_progress(
            10,
            "Preparing connection..."
        )

        self.write({
            "state": "configuration",
        })

        return True


    # ------------------------------------------------------------

    def action_authorize(self):
        """
        Generates authorization URL.
        """

        self.ensure_one()

        try:

            self._update_progress(
                20,
                "Generating authorization URL..."
            )

            provider = self._provider()

            authorization_url = provider.get_authorization_url(
                self.company_id,
            )

            self.write({

                "authorization_url":
                    authorization_url,

                "state":
                    "authorization",

            })

            return {
                "type": "ir.actions.act_url",
                "url": authorization_url,
                "target": "new",
            }

        except Exception as error:

            self._set_error(str(error))

            raise


    # ------------------------------------------------------------

    def action_connect(self):
        """
        Exchanges authorization code
        for access token.
        """

        self.ensure_one()

        try:

            self._update_progress(
                45,
                "Connecting with marketplace..."
            )

            auth_service = self.env[
                "ml.auth.service"
            ]

            credentials = auth_service.authenticate(
                connector=self.connector_id,
                authorization_code=self.authorization_code,
            )

            self.write({

                "token_received":
                    True,

                "connection_success":
                    True,

                "state":
                    "connecting",

            })

            self._credentials = credentials

            return True

        except Exception as error:

            self._set_error(str(error))

            raise


    # ------------------------------------------------------------

    def action_validate(self):
        """
        Validates user account.
        """

        self.ensure_one()

        try:

            self._update_progress(
                70,
                "Validating account..."
            )

            user_service = self.env[
                "ml.user.service"
            ]

            user = user_service.get_me(
                credentials=self._credentials,
            )

            self.write({

                "external_user_id":
                    user.get("id"),

                "external_username":
                    user.get("nickname"),

                "external_email":
                    user.get("email"),

                "marketplace_name":
                    user.get("site_name"),

                "marketplace_country":
                    user.get("country"),

                "marketplace_currency":
                    user.get("currency"),

                "validation_success":
                    True,

                "state":
                    "validating",

            })

            self._update_progress(
                90,
                "Account validated."
            )

            return True

        except Exception as error:

            self._set_error(str(error))

            raise


    # ------------------------------------------------------------

    def action_finish(self):
        """
        Creates or updates SCE account.
        """

        self.ensure_one()

        try:

            self._update_progress(
                95,
                "Saving configuration..."
            )

            if self.create_new_account:

                account = self.env[
                    "sce.account"
                ].create({

                    "name":
                        self.account_name
                        or
                        self.external_username,

                    "connector_id":
                        self.connector_id.id,

                    "company_id":
                        self.company_id.id,

                    "external_user_id":
                        self.external_user_id,

                    "external_user_name":
                        self.external_username,

                    "external_email":
                        self.external_email,

                    "state":
                        "connected",

                })

            else:

                account = self.account_id

                account.write({

                    "external_user_id":
                        self.external_user_id,

                    "external_user_name":
                        self.external_username,

                    "external_email":
                        self.external_email,

                    "state":
                        "connected",

                })

            self.write({

                "account_id":
                    account.id,

                "state":
                    "finished",

                "progress":
                    100,

                "message":
                    "Connection completed successfully.",

            })

            self.env[
                "sce.log"
            ].log_info(

                "Marketplace connected successfully.",

                account_id=account.id,

                connector_id=self.connector_id.id,

                category="connection",

            )

            return {

                "type":
                    "ir.actions.act_window",

                "res_model":
                    "sce.account",

                "res_id":
                    account.id,

                "view_mode":
                    "form",

            }

        except Exception as error:

            self._set_error(str(error))

            raise


    # ------------------------------------------------------------

    def action_cancel(self):
        """
        Cancels wizard.
        """

        self.ensure_one()

        self._reset()

        return {
            "type": "ir.actions.act_window_close",
        }


    # ============================================================
    # Complete Flow
    # ============================================================

    def action_connect_now(self):
        """
        Executes complete connection flow.
        """

        self.ensure_one()

        self.action_start()

        self.action_authorize()

        return True