# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Internal Event Listener
"""

from __future__ import annotations

from odoo import api, fields, models



class SCEEventListener(models.Model):
    """
    Internal SCE event dispatcher.
    """

    _name = "sce.event.listener"

    _description = "SCE Event Listener"

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
        string="Event Name",
        compute="_compute_name",
        store=True,
    )


    event = fields.Char(
        string="Event",
        required=True,
        index=True,
        tracking=True,
        help="Internal Odoo event name.",
    )


    description = fields.Text(
        string="Description",
    )


    active = fields.Boolean(
        default=True,
    )


    # -------------------------------------------------------------------------
    # Target Model
    # -------------------------------------------------------------------------

    model_name = fields.Char(
        string="Odoo Model",
        required=True,
        index=True,
        help="Model that generates the event.",
    )


    record_id = fields.Integer(
        string="Record ID",
        index=True,
    )


    # -------------------------------------------------------------------------
    # SCE Routing
    # -------------------------------------------------------------------------

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


    account_id = fields.Many2one(
        "sce.account",
        string="Account",
        index=True,
    )


    # -------------------------------------------------------------------------
    # Processing
    # -------------------------------------------------------------------------

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("ignored", "Ignored"),
        ],
        default="pending",
        required=True,
        index=True,
    )


    job_id = fields.Many2one(
        "sce.job",
        string="Generated Job",
        ondelete="set null",
    )


    queue_id = fields.Many2one(
        "sce.queue",
        string="Generated Queue",
        ondelete="set null",
    )

        # -------------------------------------------------------------------------
    # Event Dispatch
    # -------------------------------------------------------------------------

    def dispatch(self):

        self.ensure_one()


        if not self.active:

            self.state = "ignored"

            return False


        if self.state not in (
            "pending",
            "failed",
        ):

            raise ValueError(
                "Event cannot be dispatched."
            )


        self.write({

            "state":
                "processing",

        })


        try:


            job = self.create_job()


            queue = self.create_queue(
                job
            )


            self.write({

                "job_id":
                    job.id,

                "queue_id":
                    queue.id,

                "state":
                    "done",

            })


            return queue



        except Exception as error:


            self.write({

                "state":
                    "failed",

            })


            self.env[
                "sce.log"
            ].log_exception(
                error,
                category="business",
                account_id=self.account_id.id
                if self.account_id
                else False,
            )


            raise



    # -------------------------------------------------------------------------
    # Job Creation
    # -------------------------------------------------------------------------

    def create_job(self):

        self.ensure_one()


        return self.env[
            "sce.job"
        ].create({

            "type":
                self.event,

            "account_id":
                self.account_id.id,

            "payload": {

                "model":
                    self.model_name,

                "record_id":
                    self.record_id,

                "event":
                    self.event,

            },

        })



    # -------------------------------------------------------------------------
    # Queue Creation
    # -------------------------------------------------------------------------

    def create_queue(
        self,
        job,
    ):

        self.ensure_one()


        return self.env[
            "sce.queue"
        ].create({

            "action":
                self.event,

            "job_id":
                job.id,

            "account_id":
                self.account_id.id,

            "payload": {

                "model":
                    self.model_name,

                "record_id":
                    self.record_id,

            },

        })



    # -------------------------------------------------------------------------
    # Event Emit Helper
    # -------------------------------------------------------------------------

    @api.model
    def emit(
        self,
        event,
        model_name,
        record_id,
        account=None,
        connector=None,
        plugin=None,
    ):

        listener = self.create({

            "event":
                event,

            "model_name":
                model_name,

            "record_id":
                record_id,

            "account_id":
                account.id
                if account
                else False,

            "connector_id":
                connector.id
                if connector
                else False,

            "plugin_id":
                plugin.id
                if plugin
                else False,

        })


        return listener.dispatch()



    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "event",
        "model_name",
        "record_id",
    )
    def _compute_name(self):

        for listener in self:

            listener.name = (

                "%s [%s:%s]"

                %

                (

                    listener.event,

                    listener.model_name,

                    listener.record_id,

                )

            )



    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    @api.model
    def get_pending(
        self,
        limit=100,
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
                "create_date asc",

            limit=limit,

        )



    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_dispatch(self):

        self.ensure_one()

        return self.dispatch()



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "event",
        "model_name",
    )
    def _check_event_data(self):

        for event in self:

            if not event.event:

                raise ValueError(
                    "Event name is required."
                )


            if not event.model_name:

                raise ValueError(
                    "Model name is required."
                )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [

        (

            "sce_event_unique",

            "unique(event, model_name, record_id)",

            "This event was already registered.",

        ),

    ]