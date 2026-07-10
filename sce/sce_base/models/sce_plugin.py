# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Plugin Registry
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEPlugin(models.Model):
    """
    Registered SCE plugin.

    A plugin represents a connector implementation.
    """

    _name = "sce.plugin"

    _description = "SCE Plugin"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = "name"


    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Plugin Name",
        required=True,
        tracking=True,
    )


    code = fields.Char(
        string="Plugin Code",
        required=True,
        index=True,
        tracking=True,
        help="Unique plugin identifier.",
    )


    version = fields.Char(
        string="Version",
        default="1.0.0",
    )


    author = fields.Char(
        string="Author",
        default="Softwork",
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


    # -------------------------------------------------------------------------
    # Technical
    # -------------------------------------------------------------------------

    provider_model = fields.Char(
        string="Provider Model",
        required=True,
        help="Technical provider model.",
    )


    connector_code = fields.Char(
        string="Connector Code",
        required=True,
        index=True,
    )


    installed = fields.Boolean(
        string="Installed",
        default=False,
        tracking=True,
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

    connector_ids = fields.One2many(
        "sce.connector",
        "plugin_id",
        string="Connectors",
    )


    connector_count = fields.Integer(
        compute="_compute_statistics",
    )


    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------

    capability_ids = fields.One2many(
        "sce.plugin.capability",
        "plugin_id",
        string="Capabilities",
    )


    capability_count = fields.Integer(
        compute="_compute_statistics",
    )


    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    config_schema = fields.Json(
        string="Configuration Schema",
        default=dict,
    )


    configuration = fields.Json(
        string="Configuration",
        default=dict,
    )


    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    job_count = fields.Integer(
        compute="_compute_statistics",
    )


    account_count = fields.Integer(
        compute="_compute_statistics",
    )


    log_count = fields.Integer(
        compute="_compute_statistics",
    )


    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "connector_ids",
        "connector_ids.account_ids",
        "connector_ids.account_ids.job_ids",
        "connector_ids.account_ids.log_ids",
        "capability_ids",
    )
    def _compute_statistics(self):

        Job = self.env["sce.job"]

        Log = self.env["sce.log"]

        for plugin in self:

            plugin.connector_count = len(
                plugin.connector_ids
            )


            plugin.capability_count = len(
                plugin.capability_ids
            )


            plugin.account_count = sum(
                len(connector.account_ids)
                for connector in plugin.connector_ids
            )


            plugin.job_count = Job.search_count([
                (
                    "connector_id",
                    "in",
                    plugin.connector_ids.ids,
                )
            ])


            plugin.log_count = Log.search_count([
                (
                    "connector_id",
                    "in",
                    plugin.connector_ids.ids,
                )
            ])

                # -------------------------------------------------------------------------
    # Provider
    # -------------------------------------------------------------------------

    def provider(self):
        """
        Returns provider implementation.
        """

        self.ensure_one()

        if not self.provider_model:
            raise ValueError(
                "Provider model is not configured."
            )

        provider = self.env[
            self.provider_model
        ]

        return provider


    # -------------------------------------------------------------------------

    def get_provider(self):
        """
        Alias for provider().
        """

        self.ensure_one()

        return self.provider()


    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------

    def capabilities(self):
        """
        Returns provider capabilities.
        """

        self.ensure_one()

        provider = self.provider()

        return provider.capabilities()


    # -------------------------------------------------------------------------

    def has_capability(
        self,
        capability,
    ):
        """
        Checks if plugin supports capability.
        """

        self.ensure_one()

        return capability in self.capabilities()


    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_configuration(self):
        """
        Validates plugin configuration.
        """

        self.ensure_one()

        provider = self.provider()

        schema = provider.get_configuration_schema()

        configuration = self.configuration or {}


        missing = []

        for field_name in schema:

            if (
                schema[field_name].get("required")
                and not configuration.get(field_name)
            ):
                missing.append(
                    field_name
                )


        if missing:

            raise ValueError(
                "Missing configuration fields: %s"
                % ", ".join(missing)
            )


        return True


    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def install(self):

        self.ensure_one()

        self.validate_configuration()

        self.write({

            "installed": True,

            "state": "installed",

        })

        return True


    # -------------------------------------------------------------------------

    def enable(self):

        self.ensure_one()

        if not self.installed:

            raise ValueError(
                "Plugin must be installed first."
            )


        self.write({

            "state": "enabled",

        })


        return True


    # -------------------------------------------------------------------------

    def disable(self):

        self.ensure_one()

        self.write({

            "state": "disabled",

        })


        return True

            # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_install(self):

        self.ensure_one()

        return self.install()


    # -------------------------------------------------------------------------

    def action_enable(self):

        self.ensure_one()

        return self.enable()


    # -------------------------------------------------------------------------

    def action_disable(self):

        self.ensure_one()

        return self.disable()


    # -------------------------------------------------------------------------

    def action_test_connection(self):

        self.ensure_one()

        provider = self.provider()

        return provider.test_connection(
            self,
        )


    # -------------------------------------------------------------------------

    def action_health_check(self):

        self.ensure_one()

        provider = self.provider()

        return provider.health_check(
            self,
        )


    # -------------------------------------------------------------------------

    def action_synchronize(self):

        self.ensure_one()

        provider = self.provider()

        return provider.synchronize(
            self,
        )


    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        for plugin in records:

            if plugin.code:

                plugin.code = (
                    plugin.code
                    .lower()
                    .strip()
                )

        return records


    # -------------------------------------------------------------------------

    def write(self, vals):

        if vals.get("code"):

            vals["code"] = (
                vals["code"]
                .lower()
                .strip()
            )

        return super().write(vals)


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

        default.setdefault(
            "installed",
            False,
        )

        return super().copy(
            default
        )


    # -------------------------------------------------------------------------

    def unlink(self):

        for plugin in self:

            if plugin.connector_ids:

                raise ValueError(
                    "Cannot delete plugin with connectors."
                )

        return super().unlink()


    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("code")
    def _check_code(self):

        for plugin in self:

            if not plugin.code:

                continue


            if " " in plugin.code:

                raise ValueError(
                    "Plugin code cannot contain spaces."
                )


    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    def name_get(self):

        result = []

        for plugin in self:

            name = "[%s] %s" % (
                plugin.code.upper(),
                plugin.name,
            )

            result.append(
                (
                    plugin.id,
                    name,
                )
            )

        return result


    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (
            "sce_plugin_code_unique",
            "unique(code)",
            "Plugin code must be unique.",
        ),

        (
            "sce_plugin_connector_unique",
            "unique(connector_code)",
            "Connector code must be unique.",
        ),

    ]