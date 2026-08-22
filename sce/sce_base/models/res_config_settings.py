# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Global Settings
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # -------------------------------------------------------------------------
    # General
    # -------------------------------------------------------------------------

    sce_enabled = fields.Boolean(
        string="Enable Softwork Commerce Engine",
        config_parameter="sce.enabled",
        default=True,
    )

    sce_debug = fields.Boolean(
        string="Enable Debug Mode",
        config_parameter="sce.debug",
        default=False,
    )

    # -------------------------------------------------------------------------
    # Queue
    # -------------------------------------------------------------------------

    sce_queue_limit = fields.Integer(
        string="Queue Processing Limit",
        config_parameter="sce.queue_limit",
        default=50,
    )

    sce_max_retries = fields.Integer(
        string="Maximum Queue Retries",
        config_parameter="sce.max_retries",
        default=3,
    )

    sce_default_priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Critical"),
        ],
        string="Default Queue Priority",
        config_parameter="sce.default_priority",
        default="1",
    )

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    sce_log_level = fields.Selection(
        [
            ("debug", "Debug"),
            ("info", "Information"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        string="Minimum Log Level",
        config_parameter="sce.log_level",
        default="info",
    )

    sce_log_retention_days = fields.Integer(
        string="Log Retention (days)",
        config_parameter="sce.log_retention_days",
        default=90,
    )

    # -------------------------------------------------------------------------
    # Webhooks
    # -------------------------------------------------------------------------

    sce_webhook_retention_days = fields.Integer(
        string="Webhook Retention (days)",
        config_parameter="sce.webhook_retention_days",
        default=30,
    )

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------

    sce_worker_timeout = fields.Integer(
        string="Worker Timeout (seconds)",
        config_parameter="sce.worker_timeout",
        default=300,
    )

    sce_chunk_size = fields.Integer(
        string="Synchronization Chunk Size",
        config_parameter="sce.chunk_size",
        default=100,
    )

    # -------------------------------------------------------------------------
    # HTTP
    # -------------------------------------------------------------------------

    sce_http_timeout = fields.Integer(
        string="HTTP Timeout (seconds)",
        config_parameter="sce.http_timeout",
        default=60,
    )

    sce_http_retries = fields.Integer(
        string="HTTP Retry Attempts",
        config_parameter="sce.http_retries",
        default=3,
    )