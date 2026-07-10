# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Webhook Management
"""

from __future__ import annotations

from odoo import api, fields, models


class SCEWebhook(models.Model):
    """
    External webhook events.
    """

    _name = "sce.webhook"

    _description = "SCE Webhook"

    _inherit = [
        "mail.thread",
    ]

    _order = (
        "create_date desc"
    )



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Webhook Name",
        compute="_compute_name",
        store=True,
    )


    event = fields.Char(
        string="Event",
        required=True,
        index=True,
        tracking=True,
        help="External event name.",
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
        ondelete="cascade",
        index=True,
    )


    connector_id = fields.Many2one(
        "sce.connector",
        related="account_id.connector_id",
        store=True,
        readonly=True,
    )


    plugin_id = fields.Many2one(
        "sce.plugin",
        related="account_id.plugin_id",
        store=True,
        readonly=True,
    )


    job_id = fields.Many2one(
        "sce.job",
        string="Generated Job",
        ondelete="set null",
        index=True,
    )


    queue_id = fields.Many2one(
        "sce.queue",
        string="Generated Queue Item",
        ondelete="set null",
        index=True,
    )


    # -------------------------------------------------------------------------
    # Webhook State
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("received", "Received"),
            ("processing", "Processing"),
            ("processed", "Processed"),
            ("failed", "Failed"),
            ("ignored", "Ignored"),
        ],
        default="received",
        required=True,
        tracking=True,
        index=True,
    )

        # -------------------------------------------------------------------------
    # Incoming Data
    # -------------------------------------------------------------------------

    payload = fields.Json(
        string="Payload",
        default=dict,
        help="Webhook body received.",
    )


    headers = fields.Json(
        string="HTTP Headers",
        default=dict,
        help="HTTP headers received.",
    )


    query_params = fields.Json(
        string="Query Parameters",
        default=dict,
    )


    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------

    signature = fields.Char(
        string="Signature",
    )


    signature_valid = fields.Boolean(
        string="Signature Valid",
        default=False,
    )


    source_ip = fields.Char(
        string="Source IP",
    )


    user_agent = fields.Char(
        string="User Agent",
    )


    # -------------------------------------------------------------------------
    # External Information
    # -------------------------------------------------------------------------

    external_id = fields.Char(
        string="External Event ID",
        index=True,
    )


    external_resource = fields.Char(
        string="External Resource",
        help="External object reference.",
    )


    external_type = fields.Char(
        string="External Type",
    )


    # -------------------------------------------------------------------------
    # Processing Information
    # -------------------------------------------------------------------------

    received_at = fields.Datetime(
        string="Received At",
        default=fields.Datetime.now,
        readonly=True,
    )


    processed_at = fields.Datetime(
        string="Processed At",
        readonly=True,
    )


    processing_time = fields.Float(
        string="Processing Time (seconds)",
        readonly=True,
    )


    response_status = fields.Integer(
        string="Response Status",
        readonly=True,
    )


    response_body = fields.Json(
        string="Response Body",
        default=dict,
        readonly=True,
    )


    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    error_message = fields.Text(
        string="Error Message",
        readonly=True,
    )


    error_traceback = fields.Text(
        string="Error Traceback",
        readonly=True,
    )

        # -------------------------------------------------------------------------
    # Webhook Processing
    # -------------------------------------------------------------------------

    def validate_signature(self):

        self.ensure_one()


        """
        Base signature validation.

        Each connector can override
        this method.
        """


        if not self.signature:

            self.signature_valid = False

            return False


        self.signature_valid = True


        return True



    # -------------------------------------------------------------------------

    def process(self):

        self.ensure_one()


        if self.state not in (
            "received",
            "failed",
        ):

            raise ValueError(
                "Webhook cannot be processed."
            )


        self.write({

            "state":
                "processing",

        })


        try:


            if not self.validate_signature():

                self.write({

                    "state":
                        "failed",

                    "error_message":
                        "Invalid signature",

                })

                return False



            job = self.create_job()


            queue = self.create_queue(
                job
            )


            self.write({

                "job_id":
                    job.id,

                "queue_id":
                    queue.id,

            })


            self.finish_success()



            return queue



        except Exception as error:


            self.finish_error(
                error
            )


            raise



    # -------------------------------------------------------------------------
    # Job Creation
    # -------------------------------------------------------------------------

    def create_job(self):

        self.ensure_one()


        job = self.env[
            "sce.job"
        ].create({

            "type":
                self.event,

            "account_id":
                self.account_id.id,

            "payload":
                self.payload,

        })


        return job



    # -------------------------------------------------------------------------
    # Queue Creation
    # -------------------------------------------------------------------------

    def create_queue(
        self,
        job,
    ):

        self.ensure_one()


        queue = self.env[
            "sce.queue"
        ].create({

            "action":
                self.event,

            "account_id":
                self.account_id.id,

            "job_id":
                job.id,

            "payload":
                self.payload,

            "priority":
                "2",

        })


        return queue



    # -------------------------------------------------------------------------
    # Finish Processing
    # -------------------------------------------------------------------------

    def finish_success(self):

        self.ensure_one()


        now = fields.Datetime.now()


        duration = 0


        if self.received_at:

            duration = (

                (
                    now
                    -
                    self.received_at

                ).total_seconds()

            )


        self.write({

            "state":
                "processed",

            "processed_at":
                now,

            "processing_time":
                duration,

            "response_status":
                200,

        })


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

            "error_message":
                str(error),

            "error_traceback":
                traceback.format_exc(),

            "response_status":
                500,

        })


        return True

            # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "event",
        "external_id",
        "account_id",
    )
    def _compute_name(self):

        for webhook in self:


            if webhook.account_id:

                webhook.name = (

                    "%s - %s"

                    %

                    (

                        webhook.account_id.name,

                        webhook.event,

                    )

                )


            else:

                webhook.name = (

                    webhook.event

                    or

                    "SCE Webhook"

                )



    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    @api.model
    def get_pending(
        self,
        limit=100,
    ):
        """
        Returns received webhooks.
        """

        return self.search(

            [

                (
                    "state",
                    "=",
                    "received",
                )

            ],

            order=
                "create_date asc",

            limit=limit,

        )



    # -------------------------------------------------------------------------

    @api.model
    def get_failed(
        self,
        limit=100,
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
    # Statistics
    # -------------------------------------------------------------------------

    @api.model
    def count_events(
        self,
        account=None,
    ):

        domain = []


        if account:

            domain.append(

                (
                    "account_id",
                    "=",
                    account.id,
                )

            )


        return self.search_count(
            domain
        )



    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    @api.model
    def cleanup_old_webhooks(
        self,
        days=30,
    ):
        """
        Removes processed webhook events.
        """


        limit_date = fields.Datetime.subtract(

            fields.Datetime.now(),

            days=days,

        )


        records = self.search(

            [

                (
                    "state",
                    "=",
                    "processed",
                ),

                (
                    "create_date",
                    "<",
                    limit_date,
                ),

            ]

        )


        records.unlink()


        return True



    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_job(self):

        self.ensure_one()


        if not self.job_id:

            return False


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Generated Job",

            "res_model":
                "sce.job",

            "view_mode":
                "form",

            "res_id":
                self.job_id.id,

        }



    # -------------------------------------------------------------------------

    def action_open_queue(self):

        self.ensure_one()


        if not self.queue_id:

            return False


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Queue Item",

            "res_model":
                "sce.queue",

            "view_mode":
                "form",

            "res_id":
                self.queue_id.id,

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
        "state",
    )
    def _check_state(self):

        valid_states = [

            "received",

            "processing",

            "processed",

            "failed",

            "ignored",

        ]


        for webhook in self:

            if webhook.state not in valid_states:

                raise ValueError(
                    "Invalid webhook state."
                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (

            "sce_webhook_external_unique",

            "unique(account_id, external_id)",

            "External webhook event already exists.",

        ),

    ]