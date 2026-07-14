# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Logger Service
"""


import traceback


from odoo import (
    api,
    models,
)


from ..exceptions import (
    SCEException,
)



class SCELoggerService(models.AbstractModel):

    _name = "sce.logger.service"

    _description = "SCE Logger Service"



    # -------------------------------------------------------------------------
    # Generic
    # -------------------------------------------------------------------------

    @api.model
    def log(
        self,
        level,
        message,
        **kwargs,
    ):
        """
        Generic SCE logger.
        """


        return self.env[
            "sce.log"
        ].create_log(

            level,

            message,

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Levels
    # -------------------------------------------------------------------------

    @api.model
    def debug(
        self,
        message,
        **kwargs,
    ):

        return self.log(
            "debug",
            message,
            **kwargs,
        )



    @api.model
    def info(
        self,
        message,
        **kwargs,
    ):

        return self.log(
            "info",
            message,
            **kwargs,
        )



    @api.model
    def warning(
        self,
        message,
        **kwargs,
    ):

        return self.log(
            "warning",
            message,
            **kwargs,
        )



    @api.model
    def error(
        self,
        message,
        **kwargs,
    ):

        return self.log(
            "error",
            message,
            **kwargs,
        )



    @api.model
    def critical(
        self,
        message,
        **kwargs,
    ):

        return self.log(
            "critical",
            message,
            **kwargs,
        )



    # -------------------------------------------------------------------------
    # Exception
    # -------------------------------------------------------------------------

    @api.model
    def exception(
        self,
        error,
        **kwargs,
    ):
        """
        Logs Python/SCE exceptions.
        """


        values = {}

        values.update(
            kwargs
        )


        if isinstance(
            error,
            SCEException,
        ):

            values.update({

                "provider":
                    getattr(
                        error,
                        "provider",
                        None,
                    ),

                "endpoint":
                    getattr(
                        error,
                        "endpoint",
                        None,
                    ),

                "operation":
                    getattr(
                        error,
                        "operation",
                        None,
                    ),

                "job_id":
                    getattr(
                        error,
                        "job_id",
                        None,
                    ),

            })


        values["traceback"] = (
            traceback.format_exc()
        )


        return self.env[
            "sce.log"
        ].log_exception(

            error,

            **values,

        )



    # -------------------------------------------------------------------------
    # Context Logger
    # -------------------------------------------------------------------------

    @api.model
    def for_account(
        self,
        account,
    ):

        return SCELoggerContext(

            self.env,

            {

                "account_id":
                    account.id,

            }

        )





class SCELoggerContext:
    """
    Contextual logger helper.
    """



    def __init__(
        self,
        env,
        context,
    ):

        self.env = env

        self.context = context



    def debug(
        self,
        message,
        **kwargs,
    ):

        return self._call(
            "debug",
            message,
            kwargs,
        )



    def info(
        self,
        message,
        **kwargs,
    ):

        return self._call(
            "info",
            message,
            kwargs,
        )



    def warning(
        self,
        message,
        **kwargs,
    ):

        return self._call(
            "warning",
            message,
            kwargs,
        )



    def error(
        self,
        message,
        **kwargs,
    ):

        return self._call(
            "error",
            message,
            kwargs,
        )



    def exception(
        self,
        error,
        **kwargs,
    ):

        return self.env[
            "sce.logger.service"
        ].exception(

            error,

            **self._merge(
                kwargs
            ),

        )



    def _call(
        self,
        method,
        message,
        values,
    ):

        return getattr(
            self.env[
                "sce.logger.service"
            ],
            method,
        )(
            message,
            **self._merge(
                values
            ),
        )



    def _merge(
        self,
        values,
    ):

        result = {}

        result.update(
            self.context
        )

        result.update(
            values
        )

        return result