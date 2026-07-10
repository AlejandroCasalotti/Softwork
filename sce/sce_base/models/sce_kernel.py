# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Kernel Engine
"""

from __future__ import annotations

from odoo import api, models


class SCEKernel(models.AbstractModel):
    """
    Central engine for SCE framework.

    Responsible for resolving plugins,
    providers and executing operations.
    """

    _name = "sce.kernel"

    _description = "SCE Kernel"


    # -------------------------------------------------------------------------
    # Plugin Registry
    # -------------------------------------------------------------------------

    def get_plugin(
        self,
        code,
    ):
        """
        Returns plugin by code.
        """

        plugin = self.env[
            "sce.plugin"
        ].search(
            [
                (
                    "code",
                    "=",
                    code,
                )
            ],
            limit=1,
        )


        if not plugin:

            raise ValueError(
                "Plugin not found: %s"
                % code
            )


        if not plugin.active:

            raise ValueError(
                "Plugin is inactive: %s"
                % code
            )


        return plugin



    # -------------------------------------------------------------------------

    def get_provider(
        self,
        code,
    ):
        """
        Returns provider instance.
        """

        plugin = self.get_plugin(
            code,
        )


        return plugin.provider()



    # -------------------------------------------------------------------------
    # Connector Resolution
    # -------------------------------------------------------------------------

    def get_connector(
        self,
        code,
    ):
        """
        Returns connector by code.
        """

        connector = self.env[
            "sce.connector"
        ].search(
            [
                (
                    "code",
                    "=",
                    code,
                )
            ],
            limit=1,
        )


        if not connector:

            raise ValueError(
                "Connector not found: %s"
                % code
            )


        return connector

            # -------------------------------------------------------------------------
    # Account Resolution
    # -------------------------------------------------------------------------

    def get_account(
        self,
        account_id,
    ):
        """
        Returns SCE account.
        """

        account = self.env[
            "sce.account"
        ].browse(
            account_id
        )


        if not account.exists():

            raise ValueError(
                "Account not found: %s"
                % account_id
            )


        return account



    # -------------------------------------------------------------------------

    def find_account(
        self,
        connector_code,
        external_user_id=None,
    ):
        """
        Finds account by connector
        and optional external identifier.
        """

        domain = [

            (
                "connector_code",
                "=",
                connector_code,
            )

        ]


        if external_user_id:

            domain.append(

                (
                    "external_user_id",
                    "=",
                    external_user_id,
                )

            )


        account = self.env[
            "sce.account"
        ].search(
            domain,
            limit=1,
        )


        return account



    # -------------------------------------------------------------------------
    # Plugin Validation
    # -------------------------------------------------------------------------

    def validate_plugin(
        self,
        code,
    ):
        """
        Validates plugin availability.
        """

        plugin = self.get_plugin(
            code
        )


        if not plugin.installed:

            raise ValueError(
                "Plugin is not installed."
            )


        if plugin.state != "enabled":

            raise ValueError(
                "Plugin is not enabled."
            )


        return plugin



    # -------------------------------------------------------------------------
    # Capability Validation
    # -------------------------------------------------------------------------

    def check_capability(
        self,
        plugin_code,
        capability,
    ):
        """
        Checks plugin capability.
        """

        plugin = self.validate_plugin(
            plugin_code
        )


        if not plugin.has_capability(
            capability
        ):

            raise ValueError(

                "Plugin %s does not support %s"
                % (
                    plugin_code,
                    capability,
                )

            )


        return True



    # -------------------------------------------------------------------------
    # Provider Execution
    # -------------------------------------------------------------------------

    def execute(
        self,
        plugin_code,
        method,
        *args,
        **kwargs,
    ):
        """
        Executes provider method dynamically.
        """

        provider = self.get_provider(
            plugin_code
        )


        if not hasattr(
            provider,
            method,
        ):

            raise ValueError(

                "Provider method not found: %s"
                % method

            )


        operation = getattr(
            provider,
            method,
        )


        return operation(
            *args,
            **kwargs,
        )

            # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    def create_job(
        self,
        account,
        job_type,
        payload=None,
    ):
        """
        Creates a synchronization job.
        """

        return self.env[
            "sce.job"
        ].create({

            "account_id":
                account.id,

            "type":
                job_type,

            "payload":
                payload or {},

            "state":
                "pending",

        })


    # -------------------------------------------------------------------------

    def execute_job(
        self,
        job,
    ):
        """
        Executes a SCE job.
        """

        job.write({

            "state":
                "running",

        })


        try:

            result = self.execute(

                job.account_id.connector_code,

                job.type,

                job.account_id,

            )


            job.write({

                "state":
                    "done",

                "result":
                    result,

            })


            return result


        except Exception as error:


            job.write({

                "state":
                    "failed",

                "error":
                    str(error),

            })


            raise



    # -------------------------------------------------------------------------
    # Queue Management
    # -------------------------------------------------------------------------

    def enqueue(
        self,
        account,
        action,
        payload=None,
    ):
        """
        Adds operation to queue.
        """

        return self.env[
            "sce.queue"
        ].create({

            "account_id":
                account.id,

            "action":
                action,

            "payload":
                payload or {},

            "state":
                "pending",

        })



    # -------------------------------------------------------------------------

    def process_queue(
        self,
        limit=50,
    ):
        """
        Processes pending queue items.
        """

        queue_items = self.env[
            "sce.queue"
        ].search(
            [
                (
                    "state",
                    "=",
                    "pending",
                )
            ],
            limit=limit,
        )


        results = []


        for item in queue_items:

            try:

                item.write({

                    "state":
                        "running",

                })


                result = self.execute(

                    item.account_id.connector_code,

                    item.action,

                    item.account_id,

                )


                item.write({

                    "state":
                        "done",

                    "result":
                        result,

                })


                results.append(
                    result
                )


            except Exception as error:


                item.write({

                    "state":
                        "failed",

                    "error":
                        str(error),

                })


        return results

            # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    def log(
        self,
        level,
        message,
        *,
        account=None,
        connector=None,
        payload=None,
    ):
        """
        Creates SCE log entry.
        """

        values = {

            "level":
                level,

            "message":
                message,

            "payload":
                payload or {},

        }


        if account:

            values["account_id"] = (
                account.id
            )


        if connector:

            values["connector_id"] = (
                connector.id
            )


        return self.env[
            "sce.log"
        ].create(values)



    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def handle_error(
        self,
        error,
        *,
        account=None,
        connector=None,
        payload=None,
    ):
        """
        Handles execution errors.
        """

        self.log(

            "error",

            str(error),

            account=account,

            connector=connector,

            payload=payload,

        )


        return {

            "success":
                False,

            "error":
                str(error),

        }



    # -------------------------------------------------------------------------
    # Execution Context
    # -------------------------------------------------------------------------

    def get_context(
        self,
        account=None,
        connector=None,
    ):
        """
        Returns SCE execution context.
        """

        return {

            "account":
                account,

            "connector":
                connector,

            "company":
                self.env.company,

            "user":
                self.env.user,

        }



    # -------------------------------------------------------------------------
    # Event Dispatcher
    # -------------------------------------------------------------------------

    def dispatch_event(
        self,
        event,
        payload=None,
    ):
        """
        Dispatches internal SCE event.
        """

        listeners = self.env[
            "sce.event.listener"
        ].search(
            [
                (
                    "event",
                    "=",
                    event,
                )
            ]
        )


        results = []


        for listener in listeners:

            handler = getattr(

                listener,

                "execute",

                None,

            )


            if handler:

                results.append(

                    handler(
                        payload or {}
                    )

                )


        return results



    # -------------------------------------------------------------------------
    # Service Resolver
    # -------------------------------------------------------------------------

    def get_service(
        self,
        service_name,
    ):
        """
        Returns SCE service model.
        """

        service = self.env[
            service_name
        ]

        return service



    # -------------------------------------------------------------------------
    # Generic Call
    # -------------------------------------------------------------------------

    def call(
        self,
        model,
        method,
        *args,
        **kwargs,
    ):
        """
        Generic service execution.
        """

        service = self.get_service(
            model
        )


        if not hasattr(
            service,
            method,
        ):

            raise ValueError(

                "Method %s not found in %s"
                % (
                    method,
                    model,
                )

            )


        return getattr(
            service,
            method,
        )(
            *args,
            **kwargs,
        )