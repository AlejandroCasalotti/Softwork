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



from ..exceptions import (
    SCEAPIError,
    SCEConnectionError,
    SCEAuthenticationError,
    SCEConnectorError,
    SCEQueueError,
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



        # -------------------------------------------------
        # SCE Metadata
        # -------------------------------------------------

        for field in (
            "provider",
            "endpoint",
            "operation",
            "status_code",
            "response",
        ):

            if hasattr(
                error,
                field,
            ):

                values[field] = getattr(
                    error,
                    field,
                )



        # -------------------------------------------------
        # Context
        # -------------------------------------------------

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
    # Categories
    # -------------------------------------------------------------------------

    @api.model
    def api_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            SCEAPIError(
                message
            ),

            category="api",

            **kwargs,

        )



    @api.model
    def auth_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            SCEAuthenticationError(
                message
            ),

            category="authentication",

            **kwargs,

        )



    @api.model
    def queue_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            SCEQueueError(
                message
            ),

            category="queue",

            **kwargs,

        )



    @api.model
    def connector_error(
        self,
        message,
        **kwargs,
    ):

        return self.handle(

            SCEConnectorError(
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

            SCEConnectionError,

            TimeoutError,

        )


        if isinstance(
            error,
            retryable,
        ):

            return True



        if isinstance(
            error,
            SCEAPIError,
        ):

            status = getattr(
                error,
                "status_code",
                None,
            )


            return status in (
                429,
                500,
                502,
                503,
                504,
            )


        return False