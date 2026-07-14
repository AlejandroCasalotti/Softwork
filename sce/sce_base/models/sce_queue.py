# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Queue Management
"""

from __future__ import annotations

import traceback
import uuid

from odoo import api, fields, models


class SCEQueue(models.Model):

    """
    Internal execution queue.

    Controls asynchronous execution
    of SCE jobs.
    """

    _name = "sce.queue"

    _description = "SCE Queue"

    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    _order = "priority desc, create_date asc"


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
    # State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
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
        string="Priority",
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
    # Worker
    # -------------------------------------------------------------------------

    worker_id = fields.Char(
        readonly=True,
        copy=False,
    )


    lock_date = fields.Datetime(
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    execution_time = fields.Float(
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
                item.retry_count < item.max_retries
            )


    # -------------------------------------------------------------------------
    # Lock Management
    # -------------------------------------------------------------------------

    def acquire_lock(self):

        self.ensure_one()

        if self.state != "pending":

            raise ValueError(
                "Queue item is not available."
            )


        self.write({

            "state": "processing",

            "worker_id": str(
                uuid.uuid4()
            ),

            "lock_date":
                fields.Datetime.now(),

            "started_at":
                fields.Datetime.now(),

        })


        return True



    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def execute(self):

        self.ensure_one()


        self.acquire_lock()


        kernel = self.env[
            "sce.kernel"
        ]


        try:

            result = kernel.execute(

                self.account_id.connector_code,

                self.action,

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
    # Success
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
                    now -
                    self.started_at

                ).total_seconds()

            )


        self.write(
            values
        )


        return True



    # -------------------------------------------------------------------------
    # Error
    # -------------------------------------------------------------------------

    def finish_error(
        self,
        error,
    ):

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

            "started_at":
                False,

            "finished_at":
                False,

            "execution_time":
                0,

            "result":
                {},

            "error":
                False,

            "error_message":
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
                ),
                "|",
                (
                    "scheduled_at",
                    "=",
                    False,
                ),
                (
                    "scheduled_at",
                    "<=",
                    fields.Datetime.now(),
                ),
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

                item.name = "SCE Queue Item"



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


        vals = dict(vals)


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