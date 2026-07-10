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
    # Debug
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



    # -------------------------------------------------------------------------
    # Info
    # -------------------------------------------------------------------------

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



    # -------------------------------------------------------------------------
    # Warning
    # -------------------------------------------------------------------------

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



    # -------------------------------------------------------------------------
    # Error
    # -------------------------------------------------------------------------

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



    # -------------------------------------------------------------------------
    # Critical
    # -------------------------------------------------------------------------

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
        Logs Python exceptions.
        """


        return self.env[
            "sce.log"
        ].log_exception(

            error,

            **kwargs,

        )



    # -------------------------------------------------------------------------
    # Context Logger
    # -------------------------------------------------------------------------

    @api.model
    def for_account(
        self,
        account,
    ):
        """
        Returns contextual logger.
        """


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

        return self.env[
            "sce.logger.service"
        ].debug(

            message,

            **self._merge(
                kwargs
            ),

        )



    def info(
        self,
        message,
        **kwargs,
    ):

        return self.env[
            "sce.logger.service"
        ].info(

            message,

            **self._merge(
                kwargs
            ),

        )



    def warning(
        self,
        message,
        **kwargs,
    ):

        return self.env[
            "sce.logger.service"
        ].warning(

            message,

            **self._merge(
                kwargs
            ),

        )



    def error(
        self,
        message,
        **kwargs,
    ):

        return self.env[
            "sce.logger.service"
        ].error(

            message,

            **self._merge(
                kwargs
            ),

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