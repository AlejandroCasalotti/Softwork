# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Marketplace Connector
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEConnector(models.Model):
    """
    Registered connector.
    """

    _name = "sce.connector"

    _description = "Marketplace Connector"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = "name"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        required=True,
        tracking=True,
    )

    code = fields.Char(
        required=True,
        tracking=True,
        index=True,
    )

    version = fields.Char(
        required=True,
        default="1.0.0",
    )

    author = fields.Char()

    website = fields.Char()

    description = fields.Text()

    active = fields.Boolean(
        default=True,
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Type
    # -------------------------------------------------------------------------

    connector_type = fields.Selection(
        [
            ("marketplace", "Marketplace"),
            ("ecommerce", "eCommerce"),
            ("erp", "ERP"),
            ("other", "Other"),
        ],
        default="marketplace",
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("installed", "Installed"),
            ("enabled", "Enabled"),
            ("disabled", "Disabled"),
        ],
        default="draft",
        tracking=True,
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
        compute="_compute_statistics",
    )

    job_count = fields.Integer(
        compute="_compute_statistics",
    )

        # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    log_count = fields.Integer(
        compute="_compute_statistics",
    )

    queue_count = fields.Integer(
        compute="_compute_statistics",
    )

    webhook_count = fields.Integer(
        compute="_compute_statistics",
    )

    @api.depends(
        "account_ids",
        "account_ids.job_ids",
        "account_ids.log_ids",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]
        Log = self.env["sce.log"]
        Queue = self.env["sce.queue"]
        Webhook = self.env["sce.webhook"]

        for connector in self:

            connector.account_count = len(
                connector.account_ids
            )

            connector.job_count = Job.search_count([
                ("connector_id", "=", connector.id),
            ])

            connector.log_count = Log.search_count([
                ("connector_id", "=", connector.id),
            ])

            connector.queue_count = Queue.search_count([
                ("connector_id", "=", connector.id),
            ])

            connector.webhook_count = Webhook.search_count([
                ("connector_id", "=", connector.id),
            ])

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_install(self):
        """
        Install connector.
        """

        self.ensure_one()

        self.write({
            "state": "installed",
        })

        return True

    # -------------------------------------------------------------------------

    def action_enable(self):
        """
        Enable connector.
        """

        self.ensure_one()

        self.write({
            "state": "enabled",
        })

        return True

    # -------------------------------------------------------------------------

    def action_disable(self):
        """
        Disable connector.
        """

        self.ensure_one()

        self.write({
            "state": "disabled",
        })

        return True

    # -------------------------------------------------------------------------

    def action_open_accounts(self):

        self.ensure_one()

        return {

            "type": "ir.actions.act_window",

            "name": "Accounts",

            "res_model": "sce.account",

            "view_mode": "list,form",

            "domain": [
                ("connector_id", "=", self.id),
            ],

            "context": {
                "default_connector_id": self.id,
            },

        }

    # -------------------------------------------------------------------------

    def action_open_jobs(self):

        self.ensure_one()

        return {

            "type": "ir.actions.act_window",

            "name": "Jobs",

            "res_model": "sce.job",

            "view_mode": "list,form",

            "domain": [
                ("connector_id", "=", self.id),
            ],

        }

    # -------------------------------------------------------------------------

    def action_open_logs(self):

        self.ensure_one()

        return {

            "type": "ir.actions.act_window",

            "name": "Logs",

            "res_model": "sce.log",

            "view_mode": "list,form",

            "domain": [
                ("connector_id", "=", self.id),
            ],

        }

    # -------------------------------------------------------------------------

    def action_open_queue(self):

        self.ensure_one()

        return {

            "type": "ir.actions.act_window",

            "name": "Queue",

            "res_model": "sce.queue",

            "view_mode": "list,form",

            "domain": [
                ("connector_id", "=", self.id),
            ],

        }

    # -------------------------------------------------------------------------

    def action_open_webhooks(self):

        self.ensure_one()

        return {

            "type": "ir.actions.act_window",

            "name": "Webhooks",

            "res_model": "sce.webhook",

            "view_mode": "list,form",

            "domain": [
                ("connector_id", "=", self.id),
            ],

        }

    # -------------------------------------------------------------------------
    # Kernel
    # -------------------------------------------------------------------------

    def get_plugin(self):
        """
        Returns the plugin registered for this connector.
        """

        self.ensure_one()

        return self.env[
            "sce.kernel"
        ].get_plugin(
            self.code,
        )

            # -------------------------------------------------------------------------
    # Plugin
    # -------------------------------------------------------------------------

    def get_provider(self):
        """
        Returns the provider associated with this connector.
        """

        self.ensure_one()

        plugin = self.get_plugin()

        return plugin.provider()

    # -------------------------------------------------------------------------

    def get_capabilities(self):
        """
        Returns the connector capabilities.
        """

        self.ensure_one()

        plugin = self.get_plugin()

        return plugin.capabilities()

    # -------------------------------------------------------------------------

    def has_capability(
        self,
        capability: str,
    ) -> bool:
        """
        Checks whether the connector supports a capability.
        """

        self.ensure_one()

        return capability in self.get_capabilities()

    # -------------------------------------------------------------------------

    def supports_products(self) -> bool:

        return self.has_capability(
            "products",
        )

    # -------------------------------------------------------------------------

    def supports_orders(self) -> bool:

        return self.has_capability(
            "orders",
        )

    # -------------------------------------------------------------------------

    def supports_shipments(self) -> bool:

        return self.has_capability(
            "shipments",
        )

    # -------------------------------------------------------------------------

    def supports_stock(self) -> bool:

        return self.has_capability(
            "stock",
        )

    # -------------------------------------------------------------------------

    def supports_prices(self) -> bool:

        return self.has_capability(
            "prices",
        )

    # -------------------------------------------------------------------------

    def supports_messages(self) -> bool:

        return self.has_capability(
            "messages",
        )

    # -------------------------------------------------------------------------

    def supports_questions(self) -> bool:

        return self.has_capability(
            "questions",
        )

    # -------------------------------------------------------------------------

    def supports_returns(self) -> bool:

        return self.has_capability(
            "returns",
        )

    # -------------------------------------------------------------------------

    def supports_billing(self) -> bool:

        return self.has_capability(
            "billing",
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(self):
        """
        Validates connector configuration.
        """

        self.ensure_one()

        plugin = self.get_plugin()

        return plugin.validate_connector(
            self,
        )

    # -------------------------------------------------------------------------

    def test_connection(self):
        """
        Tests connector communication.
        """

        self.ensure_one()

        provider = self.get_provider()

        return provider.test_connection(
            self,
        )

    # -------------------------------------------------------------------------

    def synchronize(self):
        """
        Executes connector synchronization.
        """

        self.ensure_one()

        provider = self.get_provider()

        return provider.synchronize(
            self,
        )

    # -------------------------------------------------------------------------

    def health_check(self):
        """
        Executes provider health check.
        """

        self.ensure_one()

        provider = self.get_provider()

        return provider.health_check(
            self,
        )

    # -------------------------------------------------------------------------

    def get_version(self):
        """
        Returns plugin version.
        """

        self.ensure_one()

        plugin = self.get_plugin()

        return plugin.version()

    # -------------------------------------------------------------------------

    def get_display_name(self):
        """
        Returns connector display name.
        """

        self.ensure_one()

        plugin = self.get_plugin()

        return plugin.display_name()

            # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        for connector in records:

            if not connector.code:
                continue

            connector.code = connector.code.lower().strip()

        return records

    # -------------------------------------------------------------------------

    def write(self, vals):

        if "code" in vals and vals["code"]:
            vals["code"] = vals["code"].lower().strip()

        return super().write(vals)

    # -------------------------------------------------------------------------

    def unlink(self):

        for connector in self:

            if connector.account_ids:
                raise ValueError(
                    "You cannot delete a connector with existing accounts."
                )

        return super().unlink()

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("code")
    def _check_code(self):

        for connector in self:

            if not connector.code:
                continue

            if " " in connector.code:

                raise ValueError(
                    "Connector code cannot contain spaces."
                )

    # -------------------------------------------------------------------------

    _sql_constraints = [

        (
            "sce_connector_code_unique",
            "unique(code)",
            "Connector code must be unique.",
        ),

        (
            "sce_connector_company_name_unique",
            "unique(company_id, name)",
            "A connector with the same name already exists for this company.",
        ),

    ]

    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    def name_get(self):

        result = []

        for connector in self:

            name = "[%s] %s" % (
                connector.code.upper(),
                connector.name,
            )

            result.append(
                (
                    connector.id,
                    name,
                )
            )

        return result

    # -------------------------------------------------------------------------

    def copy(self, default=None):

        default = dict(default or {})

        default.setdefault(
            "name",
            "%s (Copy)" % self.name,
        )

        default.setdefault(
            "state",
            "draft",
        )

        return super().copy(default)

    # -------------------------------------------------------------------------

    def action_reset(self):
        """
        Returns the connector to draft state.
        """

        self.ensure_one()

        self.write({

            "state": "draft",

        })

        return True