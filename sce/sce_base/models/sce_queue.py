# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Queue Management
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEQueue(models.Model):
    """
    Internal execution queue.

    Controls execution scheduling
    of SCE jobs.
    """

    _name = "sce.queue"

    _description = "SCE Queue"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = (
        "priority desc, create_date asc"
    )



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Queue Item",
        compute="_compute_name",
        store=True,
    )


    action = fields.Char(
        string="Action",
        required=True,
        index=True,
        tracking=True,
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


    job_id = fields.Many2one(
        "sce.job",
        string="Job",
        ondelete="cascade",
        index=True,
    )


    connector_id = fields.Many2one(
        related="account_id.connector_id",
        store=True,
        readonly=True,
    )


    plugin_id = fields.Many2one(
        related="account_id.plugin_id",
        store=True,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Queue State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
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
        index=True,
    )


    # -------------------------------------------------------------------------
    # Scheduling
    # -------------------------------------------------------------------------

    scheduled_at = fields.Datetime(
        string="Scheduled At",
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
        help="Execution parameters.",
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
        string="Error",
        readonly=True,
    )


    error_traceback = fields.Text(
        string="Traceback",
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Retry Management
    # -------------------------------------------------------------------------

    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
    )


    max_retries = fields.Integer(
        string="Maximum Retries",
        default=3,
    )


    can_retry = fields.Boolean(
        compute="_compute_can_retry",
    )


    # -------------------------------------------------------------------------
    # Worker Control
    # -------------------------------------------------------------------------

    worker_id = fields.Char(
        string="Worker ID",
        readonly=True,
        copy=False,
    )


    lock_date = fields.Datetime(
        string="Lock Date",
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    execution_time = fields.Float(
        string="Execution Time",
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
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "retry_count",
        "max_retries",
        "state",
    )
    def _compute_can_retry(self):

        for item in self:

            item.can_retry = (

                item.state == "failed"

                and

                item.retry_count
                <
                item.max_retries

            )

                # -------------------------------------------------------------------------
    # Queue Processing
    # -------------------------------------------------------------------------

    def acquire_lock(self):

        self.ensure_one()


        if self.state != "pending":

            raise ValueError(
                "Queue item is not available."
            )


        import uuid


        self.write({

            "state":
                "processing",

            "worker_id":
                str(uuid.uuid4()),

            "lock_date":
                fields.Datetime.now(),

            "started_at":
                fields.Datetime.now(),

        })


        return True



    # -------------------------------------------------------------------------

    def execute(self):

        self.ensure_one()


        self.acquire_lock()


        kernel = self.env[
            "sce.kernel"
        ]


        try:

            result = kernel.execute(

                self.plugin_id.code,

                self.action,

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
    # Completion
    # -------------------------------------------------------------------------

    def finish_success(
        self,
        result=None,
    ):

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

            values["execution_time"] = (

                (
                    now
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


        self.write({

            "state":
                "failed",

            "finished_at":
                fields.Datetime.now(),

            "error":
                str(error),

            "error_traceback":
                traceback.format_exc(),

        })


        return True



    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    def retry(self):

        self.ensure_one()


        if not self.can_retry:

            raise ValueError(
                "Queue item cannot be retried."
            )


        self.write({

            "state":
                "pending",

            "retry_count":
                self.retry_count + 1,

            "worker_id":
                False,

            "lock_date":
                False,

            "error":
                False,

            "error_traceback":
                False,

        })


        return True

            # -------------------------------------------------------------------------
    # Batch Processing
    # -------------------------------------------------------------------------

    @api.model
    def process_queue(
        self,
        limit=50,
    ):
        """
        Process pending queue items.
        """

        items = self.search(
            [
                (
                    "state",
                    "=",
                    "pending",
                )
            ],
            order=
                "priority desc, create_date asc",
            limit=limit,
        )


        results = []


        for item in items:

            try:

                result = item.execute()

                results.append({

                    "id":
                        item.id,

                    "success":
                        True,

                    "result":
                        result,

                })


            except Exception as error:


                results.append({

                    "id":
                        item.id,

                    "success":
                        False,

                    "error":
                        str(error),

                })


        return results



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


        if self.state == "processing":

            raise ValueError(
                "Processing items cannot be cancelled."
            )


        self.write({

            "state":
                "cancelled",

        })


        return True



    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.depends(
        "action",
        "account_id",
    )
    def _compute_name(self):

        for item in self:

            if item.account_id:

                item.name = (

                    "%s - %s"

                    %

                    (
                        item.account_id.name,
                        item.action,
                    )

                )

            else:

                item.name = (
                    "SCE Queue Item"
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


        return records



    # -------------------------------------------------------------------------

    def write(
        self,
        vals,
    ):


        if vals.get("state") == "processing":

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
    def get_pending(
        self,
        limit=50,
    ):

        return self.search(
            [
                (
                    "state",
                    "=",
                    "pending",
                )
            ],
            order=
                "priority desc, create_date asc",
            limit=limit,
        )



    # -------------------------------------------------------------------------

    @api.model
    def get_processing(
        self,
    ):

        return self.search(
            [
                (
                    "state",
                    "=",
                    "processing",
                )
            ]
        )



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "max_retries",
    )
    def _check_retries(self):

        for item in self:

            if item.max_retries < 0:

                raise ValueError(
                    "Maximum retries cannot be negative."
                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (
            "sce_queue_job_action_unique",

            "unique(job_id, action)",

            "A queue item with the same action already exists for this job.",

        ),

    ]