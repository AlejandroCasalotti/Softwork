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

    _order = "create_date desc"



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
    )


    description = fields.Text()


    active = fields.Boolean(
        default=True,
    )



    # -------------------------------------------------------------------------
    # Origin
    # -------------------------------------------------------------------------

    model_name = fields.Char(
        string="Odoo Model",
        required=True,
        index=True,
    )


    record_id = fields.Integer(
        string="Record ID",
        index=True,
    )



    # -------------------------------------------------------------------------
    # Routing
    # -------------------------------------------------------------------------

    connector_id = fields.Many2one(
        "sce.connector",
        index=True,
        ondelete="set null",
    )


    plugin_id = fields.Many2one(
        "sce.plugin",
        index=True,
        ondelete="set null",
    )


    account_id = fields.Many2one(
        "sce.account",
        index=True,
        ondelete="cascade",
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
        string="State",
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


    processed_at = fields.Datetime(
        string="Processed At",
        readonly=True,
    )


    error_message = fields.Text(
        string="Error Message",
        readonly=True,
    )



    # -------------------------------------------------------------------------
    # Event Dispatch
    # -------------------------------------------------------------------------

    def dispatch(self):

        self.ensure_one()


        if not self.active:

            self.write({

                "state":
                    "ignored",

            })

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

            queue = self.create_queue()


            job = self.create_job(
                queue
            )


            self.write({

                "job_id":
                    job.id,

                "queue_id":
                    queue.id,

                "state":
                    "done",

                "processed_at":
                    fields.Datetime.now(),

            })


            return queue



        except Exception as error:


            self.write({

                "state":
                    "failed",

                "error_message":
                    str(error),

            })


            self.env[
                "sce.log"
            ].log_exception(

                error,

                category="business",

                account_id=(
                    self.account_id.id
                    if self.account_id
                    else False
                ),

                connector_id=(
                    self.connector_id.id
                    if self.connector_id
                    else False
                ),

                plugin_id=(
                    self.plugin_id.id
                    if self.plugin_id
                    else False
                ),

            )


            raise



    # -------------------------------------------------------------------------
    # Job Creation
    # -------------------------------------------------------------------------

    def create_job(
        self,
        queue,
    ):

        self.ensure_one()


        return self.env[
            "sce.job"
        ].create({

            "type":
                self.event,

            "account_id":
                self.account_id.id
                if self.account_id
                else False,

            "payload": {

                "event":
                    self.event,

                "model":
                    self.model_name,

                "record_id":
                    self.record_id,

                "queue_id":
                    queue.id,

            },

        })



    # -------------------------------------------------------------------------
    # Queue Creation
    # -------------------------------------------------------------------------

    def create_queue(self):

        self.ensure_one()


        return self.env[
            "sce.queue"
        ].create({

            "action":
                self.event,

            "account_id":
                self.account_id.id
                if self.account_id
                else False,

            "payload": {

                "event":
                    self.event,

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
        description=None,
    ):
        """
        Creates and dispatches an internal SCE event.
        """


        listener = self.create({

            "event":
                event,

            "model_name":
                model_name,

            "record_id":
                record_id,

            "description":
                description,

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
        """
        Returns pending events.
        """

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

    @api.model
    def get_failed(
        self,
        limit=100,
    ):
        """
        Returns failed events.
        """

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
    # Actions
    # -------------------------------------------------------------------------

    def action_dispatch(self):

        self.ensure_one()

        return self.dispatch()



    # -------------------------------------------------------------------------

    def action_open_job(self):

        self.ensure_one()


        if not self.job_id:

            return False


        return {

            "type":
                "ir.actions.act_window",

            "name":
                "Job",

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
                "Queue",

            "res_model":
                "sce.queue",

            "view_mode":
                "form",

            "res_id":
                self.queue_id.id,

        }



    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains(
        "event",
        "model_name",
    )
    def _check_event_data(self):

        for listener in self:


            if not listener.event:

                raise ValueError(
                    "Event name is required."
                )


            if not listener.model_name:

                raise ValueError(
                    "Model name is required."
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
    # SQL Constraints
    # -------------------------------------------------------------------------

    _event_record_required = models.Constraint(
        "CHECK(record_id IS NOT NULL)",
        "Event record identifier is required.",
    )