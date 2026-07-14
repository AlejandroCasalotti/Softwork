# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Marketplace Connector
"""

from __future__ import annotations

import re

from odoo import (
    api,
    fields,
    models,
)



class SCEConnector(models.Model):

    """
    Registered SCE connector.

    Represents an integration module/provider
    such as MercadoLibre, Shopify, Amazon, etc.
    """


    _name = "sce.connector"

    _description = "SCE Marketplace Connector"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]


    _order = "name"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(

        string="Connector Name",

        required=True,

        tracking=True,

    )



    code = fields.Char(

        string="Connector Code",

        required=True,

        index=True,

        tracking=True,

        help="Technical unique identifier.",

    )



    provider_code = fields.Char(

        string="Provider Code",

        index=True,

        help="SCE provider technical identifier.",

    )



    version = fields.Char(

        string="Version",

        default="1.0.0",

        required=True,

    )



    author = fields.Char(

        string="Author",

    )



    website = fields.Char(

        string="Website",

    )



    description = fields.Text(

        string="Description",

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
    # Plugin Relation
    # -------------------------------------------------------------------------

    plugin_id = fields.Many2one(

        "sce.plugin",

        string="Plugin",

        required=True,

        ondelete="restrict",

        tracking=True,

        index=True,

    )



    plugin_code = fields.Char(

        related="plugin_id.code",

        store=True,

        readonly=True,

        index=True,

    )



    # -------------------------------------------------------------------------
    # Connector Type
    # -------------------------------------------------------------------------

    connector_type = fields.Selection(

        [

            (
                "marketplace",
                "Marketplace",
            ),

            (
                "ecommerce",
                "eCommerce",
            ),

            (
                "erp",
                "ERP",
            ),

            (
                "payment",
                "Payment Provider",
            ),

            (
                "logistics",
                "Logistics",
            ),

            (
                "other",
                "Other",
            ),

        ],

        string="Connector Type",

        default="marketplace",

        required=True,

        tracking=True,

    )



    # -------------------------------------------------------------------------
    # Lifecycle State
    # -------------------------------------------------------------------------

    state = fields.Selection(

        [

            (
                "draft",
                "Draft",
            ),

            (
                "installed",
                "Installed",
            ),

            (
                "enabled",
                "Enabled",
            ),

            (
                "disabled",
                "Disabled",
            ),

            (
                "error",
                "Error",
            ),

        ],

        string="Status",

        default="draft",

        required=True,

        tracking=True,

        index=True,

    )



    error_message = fields.Text(

        string="Error Message",

        readonly=True,

    )



    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_ids = fields.One2many(

        "sce.account",

        "connector_id",

        string="Accounts",

    )


    account_count = fields.Integer(

        string="Accounts",

        compute="_compute_statistics",

    )


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
    # Statistics
    # -------------------------------------------------------------------------

    @api.depends(
        "account_ids",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]

        Queue = self.env["sce.queue"]

        Log = self.env["sce.log"]

        Webhook = self.env["sce.webhook"]


        for connector in self:


            connector.account_count = len(
                connector.account_ids
            )


            connector.job_count = Job.search_count(
                [
                    (
                        "connector_id",
                        "=",
                        connector.id,
                    )
                ]
            )


            connector.queue_count = Queue.search_count(
                [
                    (
                        "connector_id",
                        "=",
                        connector.id,
                    )
                ]
            )


            connector.log_count = Log.search_count(
                [
                    (
                        "connector_id",
                        "=",
                        connector.id,
                    )
                ]
            )


            connector.webhook_count = Webhook.search_count(
                [
                    (
                        "connector_id",
                        "=",
                        connector.id,
                    )
                ]
            )



    # -------------------------------------------------------------------------
    # Kernel Integration
    # -------------------------------------------------------------------------

    def get_plugin(self):

        """
        Returns associated SCE plugin.
        """

        self.ensure_one()


        if not self.plugin_id:

            raise ValueError(

                "Connector has no plugin configured."

            )


        return self.plugin_id



    # -------------------------------------------------------------------------

    def get_provider(self):

        """
        Returns provider instance through SCE Kernel.
        """

        self.ensure_one()


        kernel = self.env[
            "sce.kernel"
        ]


        provider = kernel.get_provider(
            self.code
        )


        if not provider:

            raise ValueError(

                "Provider not available for connector."

            )


        return provider



    # -------------------------------------------------------------------------
    # Provider Capabilities
    # -------------------------------------------------------------------------

    def get_capabilities(self):

        """
        Returns provider capabilities.
        """

        self.ensure_one()


        provider = self.get_provider()


        if hasattr(
            provider,
            "get_capabilities",
        ):

            return provider.get_capabilities()


        return []



    # -------------------------------------------------------------------------

    def has_capability(
        self,
        capability,
    ):

        self.ensure_one()


        capabilities = (

            self.get_capabilities()

            or

            []

        )


        return capability in capabilities



    # -------------------------------------------------------------------------
    # Capability Helpers
    # -------------------------------------------------------------------------

    def supports_products(self):

        return self.has_capability(
            "products"
        )



    def supports_orders(self):

        return self.has_capability(
            "orders"
        )



    def supports_shipments(self):

        return self.has_capability(
            "shipments"
        )



    def supports_stock(self):

        return self.has_capability(
            "stock"
        )



    def supports_prices(self):

        return self.has_capability(
            "prices"
        )



    def supports_messages(self):

        return self.has_capability(
            "messages"
        )



    def supports_questions(self):

        return self.has_capability(
            "questions"
        )



    def supports_returns(self):

        return self.has_capability(
            "returns"
        )



    def supports_billing(self):

        return self.has_capability(
            "billing"
        )



    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(self):

        self.ensure_one()


        self.validate_configuration()


        provider = self.get_provider()


        if hasattr(
            provider,
            "validate_connector",
        ):

            return provider.validate_connector(
                self
            )


        return True



    # -------------------------------------------------------------------------

    def validate_configuration(self):

        self.ensure_one()


        errors = []


        if not self.name:

            errors.append(

                "Connector name is required."

            )


        if not self.code:

            errors.append(

                "Connector code is required."

            )


        if not self.plugin_id:

            errors.append(

                "Plugin is required."

            )


        if errors:

            raise ValueError(

                "\n".join(errors)

            )


        return True



    # -------------------------------------------------------------------------
    # Provider Actions
    # -------------------------------------------------------------------------

    def test_connection(self):

        self.ensure_one()


        provider = self.get_provider()


        return provider.test_connection(
            self
        )



    # -------------------------------------------------------------------------

    def synchronize(self):

        self.ensure_one()


        provider = self.get_provider()


        return provider.synchronize(
            self
        )



    # -------------------------------------------------------------------------

    def health_check(self):

        self.ensure_one()


        provider = self.get_provider()


        if hasattr(
            provider,
            "health_check",
        ):

            return provider.health_check(
                self
            )


        return True



    # -------------------------------------------------------------------------

    def action_health_check(self):

        self.ensure_one()


        try:

            result = self.health_check()


            self.write({

                "state":
                    "enabled",

                "error_message":
                    False,

            })


            return result



        except Exception as error:


            self.write({

                "state":
                    "error",

                "error_message":
                    str(error),

            })


            raise


    # -------------------------------------------------------------------------
    # Lifecycle Actions
    # -------------------------------------------------------------------------

    def action_install(self):

        """
        Install connector.
        """

        self.ensure_one()


        self.validate_configuration()


        self.write({

            "state":
                "installed",

            "error_message":
                False,

        })


        return True



    # -------------------------------------------------------------------------

    def action_enable(self):

        """
        Enable connector.
        """

        self.ensure_one()


        if self.state == "draft":

            self.action_install()


        self.write({

            "state":
                "enabled",

            "error_message":
                False,

        })


        return True



    # -------------------------------------------------------------------------

    def action_disable(self):

        """
        Disable connector.
        """

        self.ensure_one()


        self.write({

            "state":
                "disabled",

        })


        return True



    # -------------------------------------------------------------------------

    def action_reset(self):

        """
        Return connector to draft state.
        """

        self.ensure_one()


        self.write({

            "state":
                "draft",

            "error_message":
                False,

        })


        return True



    # -------------------------------------------------------------------------
    # Navigation Actions
    # -------------------------------------------------------------------------

    def action_open_accounts(self):

        self.ensure_one()


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Accounts",

            "res_model":
                "sce.account",

            "view_mode":
                "list,form",

            "domain":
                [

                    (
                        "connector_id",
                        "=",
                        self.id,
                    )

                ],

            "context":
                {

                    "default_connector_id":
                        self.id,

                },

        }



    # -------------------------------------------------------------------------

    def action_open_jobs(self):

        self.ensure_one()


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Jobs",

            "res_model":
                "sce.job",

            "view_mode":
                "list,form",

            "domain":
                [

                    (
                        "connector_id",
                        "=",
                        self.id,
                    )

                ],

        }



    # -------------------------------------------------------------------------

    def action_open_logs(self):

        self.ensure_one()


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Logs",

            "res_model":
                "sce.log",

            "view_mode":
                "list,form",

            "domain":
                [

                    (
                        "connector_id",
                        "=",
                        self.id,
                    )

                ],

        }



    # -------------------------------------------------------------------------

    def action_open_queue(self):

        self.ensure_one()


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Queue",

            "res_model":
                "sce.queue",

            "view_mode":
                "list,form",

            "domain":
                [

                    (
                        "connector_id",
                        "=",
                        self.id,
                    )

                ],

        }



    # -------------------------------------------------------------------------

    def action_open_webhooks(self):

        self.ensure_one()


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Webhooks",

            "res_model":
                "sce.webhook",

            "view_mode":
                "list,form",

            "domain":
                [

                    (
                        "connector_id",
                        "=",
                        self.id,
                    )

                ],

        }



    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(
        self,
        vals_list,
    ):


        for values in vals_list:


            if values.get("code"):

                values["code"] = self._normalize_code(
                    values["code"]
                )


            if values.get("provider_code"):

                values["provider_code"] = self._normalize_code(
                    values["provider_code"]
                )


        return super().create(
            vals_list
        )



    # -------------------------------------------------------------------------

    def write(
        self,
        vals,
    ):


        vals = dict(vals)


        if vals.get("code"):

            vals["code"] = self._normalize_code(
                vals["code"]
            )


        if vals.get("provider_code"):

            vals["provider_code"] = self._normalize_code(
                vals["provider_code"]
            )


        return super().write(
            vals
        )



    # -------------------------------------------------------------------------

    def unlink(self):

        for connector in self:


            if connector.account_ids:


                raise ValueError(

                    "Cannot delete connector with "
                    "existing accounts."

                )


        return super().unlink()



    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_code(value):

        """
        Normalize technical codes.

        Example:
        Mercado Libre API
        ->
        mercado_libre_api
        """

        value = value.lower().strip()


        value = re.sub(
            r"[^a-z0-9_]+",
            "_",
            value,
        )


        return value.strip("_")



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "code",
    )
    def _check_code(self):

        for connector in self:


            if not connector.code:

                continue


            if connector.code != self._normalize_code(
                connector.code
            ):


                raise ValueError(

                    "Connector code contains invalid characters."

                )



    # -------------------------------------------------------------------------

    @api.constrains(
        "version",
    )
    def _check_version(self):

        for connector in self:


            if not connector.version:


                raise ValueError(

                    "Connector version is required."

                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (

            "sce_connector_company_code_unique",

            "unique(company_id, code)",

            "Connector code must be unique per company.",

        ),


        (

            "sce_connector_company_name_unique",

            "unique(company_id, name)",

            "Connector name must be unique per company.",

        ),

    ]



    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    def name_get(self):

        result = []


        for connector in self:


            name = (

                "[%s] %s"

                %

                (

                    connector.code.upper(),

                    connector.name,

                )

            )


            result.append(

                (

                    connector.id,

                    name,

                )

            )


        return result



    # -------------------------------------------------------------------------
    # Copy
    # -------------------------------------------------------------------------

    def copy(
        self,
        default=None,
    ):


        default = dict(
            default or {}
        )


        default.setdefault(

            "name",

            "%s (Copy)" % self.name,

        )


        default.setdefault(

            "code",

            "%s_copy" % self.code,

        )


        default.setdefault(

            "state",

            "draft",

        )


        default.setdefault(

            "active",

            False,

        )


        return super().copy(
            default
        )