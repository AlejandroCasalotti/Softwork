# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Webhook Management
"""

from __future__ import annotations

from odoo import api, fields, models



class SCEWebhook(models.Model):
    """
    External webhook events received by SCE.
    """


    _name = "sce.webhook"

    _description = "SCE Webhook"


    _inherit = [
        "mail.thread",
    ]


    _order = "create_date desc"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    name = fields.Char(
        string="Webhook Name",
        compute="_compute_name",
        store=True,
    )


    event = fields.Char(
        string="External Event",
        required=True,
        index=True,
        tracking=True,
    )


    external_id = fields.Char(
        string="External ID",
        index=True,
        tracking=True,
    )


    description = fields.Text()



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
        related="account_id.connector_id",
        store=True,
        readonly=True,
    )


    plugin_id = fields.Many2one(
        related="account_id.plugin_id",
        store=True,
        readonly=True,
    )


    queue_id = fields.Many2one(
        "sce.queue",
        string="Generated Queue",
        ondelete="set null",
        index=True,
    )


    job_id = fields.Many2one(
        "sce.job",
        string="Generated Job",
        ondelete="set null",
        index=True,
    )


    state = fields.Selection(
        [
            ("received", "Received"),
            ("processing", "Processing"),
            ("processed", "Processed"),
            ("failed", "Failed"),
            ("ignored", "Ignored"),
        ],
        string="Status",
        default="received",
        required=True,
        index=True,
        tracking=True,
    )


    external_resource = fields.Char(
        string="External Resource",
        index=True,
    )


    external_type = fields.Char(
        string="External Type",
        index=True,
    )


    received_at = fields.Datetime(
        string="Received At",
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


    payload = fields.Json(
        string="Payload",
        default=dict,
    )


    headers = fields.Json(
        string="Headers",
        default=dict,
    )


    query_params = fields.Json(
        string="Query Params",
        default=dict,
    )


    signature = fields.Char(
        string="Signature",
        copy=False,
    )


    signature_valid = fields.Boolean(
        string="Signature Valid",
        readonly=True,
        default=False,
    )


    source_ip = fields.Char(
        string="Source IP",
    )


    user_agent = fields.Char(
        string="User Agent",
    )


    response_body = fields.Text(
        string="Response Body",
        readonly=True,
    )


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
        """
        Validate webhook signature using connector provider.
        """

        self.ensure_one()


        provider = self.account_id.get_provider()


        result = provider.validate_webhook_signature(
            self
        )


        self.signature_valid = bool(result)


        return self.signature_valid



    # -------------------------------------------------------------------------

    def process(self):
        """
        Process incoming webhook event.

        Flow:

        Webhook
            |
            v
        Validation
            |
            v
        Job
            |
            v
        Queue
            |
            v
        Worker
        """

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


        kernel = self.env[
            "sce.kernel"
        ]


        try:


            # -------------------------------------------------------------
            # Validate signature
            # -------------------------------------------------------------

            if not self.validate_signature():


                self.write({

                    "state":
                        "failed",

                    "error_message":
                        "Invalid webhook signature",

                })


                kernel.log(

                    "warning",

                    "Webhook signature validation failed",

                    account=self.account_id,

                    connector=self.connector_id,

                    payload=self.payload,

                )


                return False



            # -------------------------------------------------------------
            # Create Job
            # -------------------------------------------------------------

            job = self.create_job()



            # -------------------------------------------------------------
            # Create Queue
            # -------------------------------------------------------------

            queue = self.create_queue(
                job
            )



            self.write({

                "job_id":
                    job.id,

                "queue_id":
                    queue.id,

            })



            # -------------------------------------------------------------
            # Logging
            # -------------------------------------------------------------

            kernel.log(

                "info",

                "Webhook queued successfully",

                account=self.account_id,

                connector=self.connector_id,

                payload={

                    "webhook_id":
                        self.id,

                    "event":
                        self.event,

                    "job_id":
                        job.id,

                    "queue_id":
                        queue.id,

                },

            )



            self.finish_success()



            return queue



        except Exception as error:


            self.finish_error(
                error
            )


            self.env[
                "sce.log"
            ].log_exception(

                error,

                category="webhook",

                account_id=
                    self.account_id.id
                    if self.account_id
                    else False,

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

                "webhook.%s"
                % self.event,


            "description":

                "Webhook execution: %s"
                % self.event,


            "account_id":

                self.account_id.id,


            "payload": {

                "webhook_id":

                    self.id,


                "event":

                    self.event,


                "external_id":

                    self.external_id,


                "external_resource":

                    self.external_resource,


                "payload":

                    self.payload,

            },

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

                "execute_job",


            "account_id":

                self.account_id.id,


            "job_id":

                job.id,


            "payload": {

                "webhook_id":

                    self.id,


                "event":

                    self.event,


            },


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
        Returns received webhooks waiting processing.
        """

        return self.search(

            [

                (
                    "state",
                    "=",
                    "received",
                )

            ],

            order="create_date asc",

            limit=limit,

        )



    # -------------------------------------------------------------------------

    @api.model
    def get_failed(
        self,
        limit=100,
    ):
        """
        Returns failed webhook events.
        """

        return self.search(

            [

                (
                    "state",
                    "=",
                    "failed",
                )

            ],

            order="create_date desc",

            limit=limit,

        )



    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    @api.model
    def count_events(
        self,
        account=None,
        event=None,
    ):
        """
        Count webhook events.
        """

        domain = []


        if account:

            domain.append(

                (
                    "account_id",
                    "=",
                    account.id,
                )

            )


        if event:

            domain.append(

                (
                    "event",
                    "=",
                    event,
                )

            )


        return self.search_count(
            domain
        )



    # -------------------------------------------------------------------------
    # Duplicate Detection
    # -------------------------------------------------------------------------

    @api.model
    def exists_external_event(
        self,
        account,
        external_id,
    ):
        """
        Check duplicated external webhook.
        """

        if not external_id:

            return False


        return bool(

            self.search_count(

                [

                    (
                        "account_id",
                        "=",
                        account.id,
                    ),

                    (
                        "external_id",
                        "=",
                        external_id,
                    ),

                ]

            )

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
        Remove processed webhook events older than given days.
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

    _external_unique = models.Constraint(
        "UNIQUE(account_id, external_id)",
        "External webhook event already exists.",
    )