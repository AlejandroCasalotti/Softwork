# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Plugin Capability
"""

from odoo import fields, models


class SCEPluginCapability(models.Model):
    """Capability declared by an SCE plugin."""

    _name = "sce.plugin.capability"
    _description = "SCE Plugin Capability"
    _order = "name"

    name = fields.Char(
        string="Capability",
        required=True,
    )

    code = fields.Char(
        string="Code",
        required=True,
    )

    description = fields.Text(
        string="Description",
    )

    plugin_id = fields.Many2one(
        "sce.plugin",
        string="Plugin",
        required=True,
        ondelete="cascade",
        index=True,
    )

    _code_plugin_unique = models.Constraint(
        "UNIQUE(plugin_id, code)",
        "Capability code must be unique per plugin.",
    )