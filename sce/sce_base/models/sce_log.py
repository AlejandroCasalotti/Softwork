# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Central Logging System
"""

from __future__ import annotations

import traceback

from odoo import (
    api,
    fields,
    models,
)



class SCELog(models.Model):

    """
    Central SCE logging system.

    Stores technical and business
    execution information.
    """


    _name = "sce.log"

    _description = "SCE Log"

    _inherit = [
        "mail.thread",
    ]


    _order = "create_date desc"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Log Title",
        compute="_compute_name",
        store=True,
    )


    message = fields.Text(
        string="Message",
        required=True,
    )



    # -------------------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------------------

    level = fields.Selection(

        [

            ("debug", "Debug"),

            ("info", "Information"),

            ("warning", "Warning"),

            ("error", "Error"),

            ("critical", "Critical"),

        ],

        string="Level",

        default="info",

        required=True,

        index=True,

        tracking=True,

    )



    category = fields.Selection(

        [

            ("system", "System"),

            ("kernel", "Kernel"),

            ("api", "API"),

            ("authentication", "Authentication"),

            ("connection", "Connection"),

            ("provider", "Provider"),

            ("connector", "Connector"),

            ("plugin", "Plugin"),

            ("queue", "Queue"),

            ("job", "Job"),

            ("synchronization", "Synchronization"),

            ("webhook", "Webhook"),

            ("business", "Business"),

        ],

        string="Category",

        default="system",

        index=True,

    )



    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_id = fields.Many2one(

        "sce.account",

        string="Account",

        ondelete="cascade",

        index=True,

    )


    connector_id = fields.Many2one(

        "sce.connector",

        string="Connector",

        index=True,

    )


    plugin_id = fields.Many2one(

        "sce.plugin",

        string="Plugin",

        index=True,

    )


    job_id = fields.Many2one(

        "sce.job",

        string="Job",

        ondelete="cascade",

        index=True,

    )


    queue_id = fields.Many2one(

        "sce.queue",

        string="Queue Item",

        ondelete="cascade",

        index=True,

    )



    # -------------------------------------------------------------------------
    # Technical Data
    # -------------------------------------------------------------------------

    payload = fields.Json(

        string="Payload",

        default=dict,

    )


    response = fields.Json(

        string="External Response",

        default=dict,

    )


    metadata = fields.Json(

        string="Metadata",

        default=dict,

    )


    provider = fields.Char(

        string="Provider",

        index=True,

    )


    endpoint = fields.Char(

        string="API Endpoint",

    )


    operation = fields.Char(

        string="Operation",

    )


    status_code = fields.Integer(

        string="HTTP Status Code",

    )



    # -------------------------------------------------------------------------
    # Exception Information
    # -------------------------------------------------------------------------

    error_code = fields.Char(

        string="Error Code",

    )


    error_type = fields.Char(

        string="Error Type",

    )


    traceback = fields.Text(

        string="Traceback",

    )



    # -------------------------------------------------------------------------
    # Environment
    # -------------------------------------------------------------------------

    company_id = fields.Many2one(

        "res.company",

        string="Company",

        default=lambda self: self.env.company,

        index=True,

    )


    user_id = fields.Many2one(

        "res.users",

        string="User",

        default=lambda self: self.env.user,

        index=True,

    )



    # -------------------------------------------------------------------------
    # External Reference
    # -------------------------------------------------------------------------

    external_id = fields.Char(

        string="External Reference",

        index=True,

    )


    external_model = fields.Char(

        string="External Model",

    )



    # -------------------------------------------------------------------------
    # Execution Metrics
    # -------------------------------------------------------------------------

    execution_id = fields.Char(

        string="Execution ID",

        index=True,

    )


    duration = fields.Float(

        string="Duration (seconds)",

    )


    records_processed = fields.Integer(

        string="Records Processed",

        default=0,

    )


    records_failed = fields.Integer(

        string="Records Failed",

        default=0,

    )


    # -------------------------------------------------------------------------
    # Generic Logger
    # -------------------------------------------------------------------------

    @api.model
    def create_log(
        self,
        level,
        message,
        **kwargs,
    ):
        """
        Creates centralized SCE log entry.
        """


        values = {

            "level":
                level,

            "message":
                message,

        }



        allowed_fields = [

            "account_id",

            "connector_id",

            "plugin_id",

            "job_id",

            "queue_id",

            "category",

            "payload",

            "response",

            "metadata",

            "provider",

            "endpoint",

            "operation",

            "status_code",

            "error_code",

            "error_type",

            "traceback",

            "external_id",

            "external_model",

            "execution_id",

            "duration",

            "records_processed",

            "records_failed",

            "company_id",

            "user_id",

        ]



        for field_name in allowed_fields:

            if field_name in kwargs:

                values[field_name] = kwargs[field_name]



        return self.create(
            values
        )



    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    @api.model
    def log_debug(
        self,
        message,
        **kwargs,
    ):

        return self.create_log(

            "debug",

            message,

            **kwargs,

        )



    @api.model
    def log_info(
        self,
        message,
        **kwargs,
    ):

        return self.create_log(

            "info",

            message,

            **kwargs,

        )



    @api.model
    def log_warning(
        self,
        message,
        **kwargs,
    ):

        return self.create_log(

            "warning",

            message,

            **kwargs,

        )



    @api.model
    def log_error(
        self,
        message,
        **kwargs,
    ):

        return self.create_log(

            "error",

            message,

            **kwargs,

        )



    @api.model
    def log_critical(
        self,
        message,
        **kwargs,
    ):

        return self.create_log(

            "critical",

            message,

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Exception Logger
    # -------------------------------------------------------------------------

    @api.model
    def log_exception(
        self,
        exception,
        **kwargs,
    ):
        """
        Logs Python exception information.
        """


        values = {

            "error_type":
                exception.__class__.__name__,

            "traceback":
                traceback.format_exc(),

        }


        values.update(kwargs)



        return self.create_log(

            "error",

            str(exception),

            **values,

        )



    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "level",
        "category",
        "message",
    )
    def _compute_name(self):

        for log in self:


            prefix = (

                log.level.upper()

                if log.level

                else

                "LOG"

            )


            if log.category:


                log.name = (

                    "[%s][%s] %s"

                    %

                    (

                        prefix,

                        log.category,

                        (log.message or "")[:80],

                    )

                )


            else:


                log.name = (

                    "[%s] %s"

                    %

                    (

                        prefix,

                        (log.message or "")[:80],

                    )

                )



    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    @api.model
    def get_errors(
        self,
        account=None,
        limit=100,
    ):
        """
        Returns error and critical logs.
        """


        domain = [

            (

                "level",

                "in",

                [

                    "error",

                    "critical",

                ],

            )

        ]


        if account:

            domain.append(

                (

                    "account_id",

                    "=",

                    account.id,

                )

            )


        return self.search(

            domain,

            order="create_date desc",

            limit=limit,

        )



    @api.model
    def get_account_logs(
        self,
        account,
        limit=100,
    ):

        return self.search(

            [

                (

                    "account_id",

                    "=",

                    account.id,

                )

            ],

            order="create_date desc",

            limit=limit,

        )



    @api.model
    def get_execution_logs(
        self,
        execution_id,
        limit=100,
    ):

        return self.search(

            [

                (

                    "execution_id",

                    "=",

                    execution_id,

                )

            ],

            order="create_date desc",

            limit=limit,

        )



    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    @api.model
    def cleanup_old_logs(
        self,
        days=90,
    ):
        """
        Removes old low priority logs.
        """


        limit_date = fields.Datetime.subtract(

            fields.Datetime.now(),

            days=days,

        )


        logs = self.search(

            [

                (

                    "create_date",

                    "<",

                    limit_date,

                ),

                (

                    "level",

                    "in",

                    [

                        "debug",

                        "info",

                    ],

                ),

            ]

        )


        logs.unlink()


        return True



    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_account(self):

        self.ensure_one()


        if not self.account_id:

            return False


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Account",

            "res_model":
                "sce.account",

            "view_mode":
                "form",

            "res_id":
                self.account_id.id,

        }



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


        return records



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "level",
    )
    def _check_level(self):

        valid_levels = [

            "debug",

            "info",

            "warning",

            "error",

            "critical",

        ]


        for log in self:

            if log.level not in valid_levels:

                raise ValueError(
                    "Invalid log level."
                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _message_required = models.Constraint(
        "CHECK(message IS NOT NULL)",
        "Log message is required.",
    )