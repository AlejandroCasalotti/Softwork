# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Exception Service
"""


import traceback


from odoo import (
    api,
    models,
)



class SCEExceptionService(models.AbstractModel):

    _name = "sce.exception.service"

    _description = "SCE Exception Service"



    # -------------------------------------------------------------------------
    # Handle Exception
    # -------------------------------------------------------------------------

    @api.model
    def handle(
        self,
        error,
        category="system",
        account=None,
        job=None,
        queue=None,
    ):
        """
        Central exception handler.
        """


        values = {

            "message":

                str(error),


            "category":

                category,


            "traceback":

                traceback.format_exc(),

        }



        if account:

            values[
                "account_id"
            ] = account.id



        if job:

            values[
                "job_id"
            ] = job.id



        if queue:

            values[
                "queue_id"
            ] = queue.id



        self.env[
            "sce.log"
        ].create_log(

            "error",

            values[
                "message"
            ],

            **values,

        )


        return True



    # -------------------------------------------------------------------------
    # API Error
    # -------------------------------------------------------------------------

    @api.model
    def api_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            Exception(
                message
            ),

            category="api",

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Authentication Error
    # -------------------------------------------------------------------------

    @api.model
    def auth_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            Exception(
                message
            ),

            category="authentication",

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Queue Error
    # -------------------------------------------------------------------------

    @api.model
    def queue_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            Exception(
                message
            ),

            category="queue",

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Connector Error
    # -------------------------------------------------------------------------

    @api.model
    def connector_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            Exception(
                message
            ),

            category="connector",

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Retry Decision
    # -------------------------------------------------------------------------

    @api.model
    def should_retry(
        self,
        error,
    ):
        """
        Determines if error is recoverable.
        """


        retryable = (

            TimeoutError,

        )


        return isinstance(
            error,
            retryable,
        )