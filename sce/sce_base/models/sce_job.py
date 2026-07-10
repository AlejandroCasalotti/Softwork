# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Job Management
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEJob(models.Model):
    """
    Internal SCE execution job.
    """

    _name = "sce.job"

    _description = "SCE Job"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = "create_date desc"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Job Name",
        compute="_compute_name",
        store=True,
    )


    type = fields.Char(
        string="Job Type",
        required=True,
        index=True,
        tracking=True,
        help="Operation to execute.",
    )


    description = fields.Text(
        string="Description",
    )


    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_id = fields.Many2one(
        "sce.account",
        string="Account",
        required=True,
        ondelete="cascade",
        index=True,
    )


    connector_id = fields.Many2one(
        related="account_id.connector_id",
        store=True,
        readonly=True,
        index=True,
    )


    plugin_id = fields.Many2one(
        related="account_id.plugin_id",
        store=True,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Execution State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("scheduled", "Scheduled"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
        index=True,
    )


    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Critical"),
        ],
        default="1",
        string="Priority",
        index=True,
    )


    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------

    scheduled_at = fields.Datetime(
        string="Scheduled Date",
    )


    started_at = fields.Datetime(
        readonly=True,
    )


    finished_at = fields.Datetime(
        readonly=True,
    )

        # -------------------------------------------------------------------------
    # Execution Data
    # -------------------------------------------------------------------------

    payload = fields.Json(
        string="Payload",
        default=dict,
        help="Input data for job execution.",
    )


    result = fields.Json(
        string="Result",
        default=dict,
        readonly=True,
    )


    response = fields.Json(
        string="Provider Response",
        default=dict,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    error = fields.Text(
        string="Error Message",
        readonly=True,
    )


    error_traceback = fields.Text(
        string="Error Traceback",
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Retry Management
    # -------------------------------------------------------------------------

    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
        readonly=True,
    )


    max_retries = fields.Integer(
        string="Maximum Retries",
        default=3,
    )


    can_retry = fields.Boolean(
        compute="_compute_can_retry",
    )


    # -------------------------------------------------------------------------
    # Execution Metrics
    # -------------------------------------------------------------------------

    duration = fields.Float(
        string="Duration (seconds)",
        readonly=True,
    )


    records_processed = fields.Integer(
        string="Records Processed",
        default=0,
        readonly=True,
    )


    records_failed = fields.Integer(
        string="Records Failed",
        default=0,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Technical Information
    # -------------------------------------------------------------------------

    worker = fields.Char(
        string="Worker",
        readonly=True,
    )


    execution_id = fields.Char(
        string="Execution ID",
        readonly=True,
        copy=False,
    )


    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "retry_count",
        "max_retries",
        "state",
    )
    def _compute_can_retry(self):

        for job in self:

            job.can_retry = (

                job.retry_count
                <
                job.max_retries

                and

                job.state == "failed"

            )

                # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def start(self):

        self.ensure_one()


        if self.state not in (
            "pending",
            "scheduled",
        ):

            raise ValueError(
                "Job cannot be started from current state."
            )


        self.write({

            "state":
                "running",

            "started_at":
                fields.Datetime.now(),

            "execution_id":
                self._generate_execution_id(),

        })


        return True



    # -------------------------------------------------------------------------

    def execute(self):

        self.ensure_one()


        self.start()


        kernel = self.env[
            "sce.kernel"
        ]


        try:

            result = kernel.execute(

                self.plugin_id.code,

                self.type,

                self.account_id,

                payload=self.payload,

            )


            self.finish_success(
                result
            )


            return result



        except Exception as error:


            self.finish_error(
                error
            )


            raise



    # -------------------------------------------------------------------------
    # Finish
    # -------------------------------------------------------------------------

    def finish_success(
        self,
        result=None,
    ):

        self.ensure_one()


        values = {

            "state":
                "done",

            "finished_at":
                fields.Datetime.now(),

            "result":
                result or {},

        }


        if self.started_at:

            values["duration"] = (

                (
                    fields.Datetime.now()
                    -
                    self.started_at

                ).total_seconds()

            )


        self.write(
            values
        )


        return True



    # -------------------------------------------------------------------------

    def finish_error(
        self,
        error,
    ):

        self.ensure_one()


        import traceback


        values = {

            "state":
                "failed",

            "finished_at":
                fields.Datetime.now(),

            "error":
                str(error),

            "error_traceback":
                traceback.format_exc(),

        }


        self.write(
            values
        )


        return True



    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    def retry(self):

        self.ensure_one()


        if not self.can_retry:

            raise ValueError(
                "Job cannot be retried."
            )


        self.write({

            "state":
                "pending",

            "retry_count":
                self.retry_count + 1,

            "error":
                False,

            "error_traceback":
                False,

        })


        return True



    # -------------------------------------------------------------------------
    # Cancel
    # -------------------------------------------------------------------------

    def cancel(self):

        self.ensure_one()


        if self.state == "running":

            raise ValueError(
                "Running jobs cannot be cancelled."
            )


        self.write({

            "state":
                "cancelled",

        })


        return True

            # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_execute(self):

        self.ensure_one()

        return self.execute()



    # -------------------------------------------------------------------------

    def action_retry(self):

        self.ensure_one()

        self.retry()

        return True



    # -------------------------------------------------------------------------

    def action_cancel(self):

        self.ensure_one()

        self.cancel()

        return True



    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _generate_execution_id(self):

        import uuid

        return str(
            uuid.uuid4()
        )



    # -------------------------------------------------------------------------

    @api.depends(
        "type",
        "account_id",
        "create_date",
    )
    def _compute_name(self):

        for job in self:

            if job.type and job.account_id:

                job.name = (

                    "%s - %s"
                    %
                    (
                        job.account_id.name,
                        job.type,
                    )

                )

            else:

                job.name = (
                    "SCE Job"
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


        for job in records:

            if not job.execution_id:

                job.execution_id = (
                    job._generate_execution_id()
                )


        return records



    # -------------------------------------------------------------------------

    def write(
        self,
        vals,
    ):

        if vals.get("state") == "running":

            vals.setdefault(
                "started_at",
                fields.Datetime.now(),
            )


        if vals.get("state") in (
            "done",
            "failed",
            "cancelled",
        ):

            vals.setdefault(
                "finished_at",
                fields.Datetime.now(),
            )


        return super().write(
            vals
        )



    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    @api.model
    def get_pending_jobs(
        self,
        limit=50,
    ):

        return self.search(
            [
                (
                    "state",
                    "in",
                    [
                        "pending",
                        "scheduled",
                    ],
                )
            ],
            order=
                "priority desc, create_date asc",
            limit=limit,
        )



    # -------------------------------------------------------------------------

    @api.model
    def get_failed_jobs(
        self,
        limit=50,
    ):

        return self.search(
            [
                (
                    "state",
                    "=",
                    "failed",
                )
            ],
            order=
                "create_date desc",
            limit=limit,
        )



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "max_retries",
    )
    def _check_max_retries(self):

        for job in self:

            if job.max_retries < 0:

                raise ValueError(
                    "Maximum retries cannot be negative."
                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (
            "sce_job_execution_unique",

            "unique(execution_id)",

            "Execution ID must be unique.",

        ),

    ]