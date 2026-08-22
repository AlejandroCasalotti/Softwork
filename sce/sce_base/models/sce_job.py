# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Job Management
"""

from __future__ import annotations

import uuid
import traceback

from odoo import (
    api,
    fields,
    models,
)


class SCEJob(models.Model):

    """
    Internal SCE execution job.

    Represents a complete business execution
    handled by SCE Kernel.
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


    queue_ids = fields.One2many(
        "sce.queue",
        "job_id",
        string="Queue Items",
    )



    # -------------------------------------------------------------------------
    # Execution State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            (
                "pending",
                "Pending",
            ),

            (
                "scheduled",
                "Scheduled",
            ),

            (
                "running",
                "Running",
            ),

            (
                "done",
                "Done",
            ),

            (
                "failed",
                "Failed",
            ),

            (
                "cancelled",
                "Cancelled",
            ),

        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
        index=True,
    )



    priority = fields.Selection(
        [
            (
                "0",
                "Low",
            ),

            (
                "1",
                "Normal",
            ),

            (
                "2",
                "High",
            ),

            (
                "3",
                "Critical",
            ),

        ],
        string="Priority",
        default="1",
        index=True,
    )



    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------

    scheduled_at = fields.Datetime(
        string="Scheduled Date",
    )


    started_at = fields.Datetime(
        string="Started At",
        readonly=True,
    )


    finished_at = fields.Datetime(
        string="Finished At",
        readonly=True,
    )



    # -------------------------------------------------------------------------
    # Execution Data
    # -------------------------------------------------------------------------

    payload = fields.Json(
        string="Payload",
        default=dict,
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
    # Errors
    # -------------------------------------------------------------------------

    error = fields.Text(
        readonly=True,
    )


    error_message = fields.Text(
        readonly=True,
    )


    error_traceback = fields.Text(
        readonly=True,
    )



    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    retry_count = fields.Integer(
        default=0,
    )


    max_retries = fields.Integer(
        default=3,
    )


    can_retry = fields.Boolean(
        compute="_compute_can_retry",
    )



    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    duration = fields.Float(
        string="Duration (seconds)",
        readonly=True,
    )


    records_processed = fields.Integer(
        default=0,
        readonly=True,
    )


    records_failed = fields.Integer(
        default=0,
        readonly=True,
    )



    # -------------------------------------------------------------------------
    # Technical
    # -------------------------------------------------------------------------

    worker = fields.Char(
        string="Worker",
        readonly=True,
    )


    execution_id = fields.Char(
        string="Execution ID",
        readonly=True,
        copy=False,
        index=True,
    )



    # -------------------------------------------------------------------------
    # Compute Retry
    # -------------------------------------------------------------------------

    @api.depends(
        "retry_count",
        "max_retries",
        "state",
    )
    def _compute_can_retry(self):

        for job in self:

            job.can_retry = (
                job.state == "failed"
                and
                job.retry_count < job.max_retries
            )



    # -------------------------------------------------------------------------
    # Start Execution
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

        })


        return True



    # -------------------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------------------

    def execute(self):

        self.ensure_one()


        self.start()


        kernel = self.env[
            "sce.kernel"
        ]


        try:

            result = kernel.execute(

                self.connector_id.code,

                self.type,

                self.account_id,

                self.payload,

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
# Finish Success
# -------------------------------------------------------------------------

    def finish_success(
        self,
        result=None,
    ):
        """
        Marks job as successfully completed.
        """

        self.ensure_one()


        now = fields.Datetime.now()


        values = {

            "state":
                "done",

            "finished_at":
                now,

            "result":
                result or {},

        }


        if self.started_at:

            values["duration"] = (

                (
                    now
                    -
                    self.started_at

                ).total_seconds()

            )


        self.write(
            values
        )


        # Central SCE logging

        self.env[
            "sce.log"
        ].create({

            "level":
                "info",

            "message":
                "Job completed successfully",

            "account_id":
                self.account_id.id,

            "payload": {

                "job_id":
                    self.id,

                "type":
                    self.type,

            },

        })


        return True



# -------------------------------------------------------------------------
# Finish Error
# -------------------------------------------------------------------------

    def finish_error(
        self,
        error,
    ):
        """
        Marks job as failed.
        """

        self.ensure_one()


        self.write({

            "state":
                "failed",

            "finished_at":
                fields.Datetime.now(),

            "error":
                str(error),

            "error_message":
                str(error),

            "error_traceback":
                traceback.format_exc(),

        })


        kernel = self.env[
            "sce.kernel"
        ]


        kernel.handle_error(

            error,

            account=self.account_id,

            connector=self.connector_id,

            payload=self.payload,

        )


        return True



# -------------------------------------------------------------------------
# Retry
# -------------------------------------------------------------------------

    def retry(self):
        """
        Returns failed job to pending.
        """

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


            "started_at":
                False,


            "finished_at":
                False,


            "duration":
                0,


            "result":
                {},


            "response":
                {},


            "error":
                False,


            "error_message":
                False,


            "error_traceback":
                False,


        })


        self.env[
            "sce.log"
        ].create({

            "level":
                "warning",

            "message":
                "Job scheduled for retry",

            "account_id":
                self.account_id.id,

            "payload": {

                "job_id":
                    self.id,

                "retry":
                    self.retry_count,

            },

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



    def action_retry(self):

        self.ensure_one()

        self.retry()

        return True



    def action_cancel(self):

        self.ensure_one()

        self.cancel()

        return True



# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

    def _generate_execution_id(self):

        return str(
            uuid.uuid4()
        )



# -------------------------------------------------------------------------
# Compute Name
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

                job.name = "SCE Job"



# -------------------------------------------------------------------------
# ORM Create
# -------------------------------------------------------------------------

    @api.model_create_multi
    def create(
        self,
        vals_list,
    ):


        for values in vals_list:


            if not values.get(
                "execution_id"
            ):

                values[
                    "execution_id"
                ] = self._generate_execution_id()



        records = super().create(
            vals_list
        )


        return records



# -------------------------------------------------------------------------
# ORM Write
# -------------------------------------------------------------------------

    def write(
        self,
        vals,
    ):


        vals = dict(vals)


        if vals.get(
            "state"
        ) == "running":


            vals.setdefault(

                "started_at",

                fields.Datetime.now(),

            )



        if vals.get(
            "state"
        ) in (

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
        """
        Returns pending and scheduled jobs.
        """


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
    def get_running_jobs(
        self,
    ):

        return self.search(

            [

                (
                    "state",
                    "=",
                    "running",
                )

            ]

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

    _execution_unique = models.Constraint(
        "UNIQUE(execution_id)",
        "Execution ID must be unique.",
    )