# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Kernel Engine
"""

from __future__ import annotations


from odoo import (
    api,
    models,
)



class SCEKernel(models.AbstractModel):
    """
    Central execution engine.

    Responsible for:

    - Plugin resolution
    - Provider execution
    - Job creation
    - Queue execution
    - Event dispatching
    - Service resolution

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

                %

                code

            )



        if not plugin.active:

            raise ValueError(

                "Plugin inactive: %s"

                %

                code

            )


        return plugin



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
    # Provider Resolver
    # -------------------------------------------------------------------------


    def get_provider(
        self,
        code,
    ):
        """
        Returns provider from plugin.
        """


        plugin = self.validate_plugin(
            code
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

                %

                code

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

                %

                account_id

            )


        return account



    # -------------------------------------------------------------------------


    def find_account(
        self,
        connector_code,
        external_user_id=None,
    ):
        """
        Finds account by connector.
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



        return self.env[
            "sce.account"
        ].search(

            domain,

            limit=1,

        )



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

                "Plugin %s does not support capability %s"

                %

                (
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

                %

                method

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
        Creates internal SCE job.
        """


        if not account:

            raise ValueError(
                "Account is required."
            )



        return self.env[
            "sce.job"
        ].create(

            {

                "account_id":

                    account.id,


                "type":

                    job_type,


                "payload":

                    payload or {},


                "state":

                    "pending",

            }

        )



    # -------------------------------------------------------------------------
    # Queue Creation
    # -------------------------------------------------------------------------


    def enqueue(
        self,
        account,
        action,
        payload=None,
    ):
        """
        Adds execution to queue.
        """


        if not account:

            raise ValueError(
                "Account is required."
            )



        return self.env[
            "sce.queue"
        ].create(

            {

                "account_id":

                    account.id,


                "action":

                    action,


                "payload":

                    payload or {},


                "state":

                    "pending",

            }

        )

    # -------------------------------------------------------------------------
    # Safe Execution Wrapper
    # -------------------------------------------------------------------------

    def safe_execute(
        self,
        plugin_code,
        method,
        *args,
        account=None,
        connector=None,
        payload=None,
        **kwargs,
    ):
        """
        Executes provider operation with
        centralized error handling and logging.
        """

        try:

            result = self.execute(
                plugin_code,
                method,
                *args,
                **kwargs,
            )


            self.log(
                "info",
                "Operation executed successfully: %s" % method,
                account=account,
                connector=connector,
                payload=payload,
            )


            return {

                "success":
                    True,

                "result":
                    result,

            }


        except Exception as error:


            return self.handle_error(

                error,

                account=account,

                connector=connector,

                payload=payload,

            )



    # -------------------------------------------------------------------------
    # Account Execution
    # -------------------------------------------------------------------------

    def execute_account_action(
        self,
        account,
        action,
        payload=None,
    ):
        """
        Executes action using account connector.
        """

        if not account:

            raise ValueError(
                "Account is required."
            )


        if not account.connector_id:

            raise ValueError(
                "Account has no connector configured."
            )


        connector = account.connector_id


        return self.safe_execute(

            connector.code,

            action,

            account,

            account=account,

            connector=connector,

            payload=payload,

        )



    # -------------------------------------------------------------------------
    # Connector Health
    # -------------------------------------------------------------------------

    def health_check(
        self,
        connector_code,
    ):
        """
        Executes connector health check.
        """

        connector = self.get_connector(
            connector_code
        )


        provider = connector.get_provider()


        if not hasattr(
            provider,
            "health_check",
        ):

            return True


        return provider.health_check(
            connector
        )



    # -------------------------------------------------------------------------
    # Connector Synchronization
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        connector_code,
        account=None,
    ):
        """
        Executes connector synchronization.
        """

        connector = self.get_connector(
            connector_code
        )


        provider = connector.get_provider()


        if account:

            return provider.synchronize(
                account
            )


        return provider.synchronize(
            connector
        )



    # -------------------------------------------------------------------------
    # Plugin Information
    # -------------------------------------------------------------------------

    def plugin_info(
        self,
        code,
    ):
        """
        Returns plugin metadata.
        """

        plugin = self.get_plugin(
            code
        )


        return {

            "name":
                plugin.name,

            "code":
                plugin.code,

            "version":
                plugin.version,

            "author":
                plugin.author,

            "state":
                plugin.state,

            "capabilities":
                plugin.capabilities(),

        }



    # -------------------------------------------------------------------------
    # Execution Context Builder
    # -------------------------------------------------------------------------

    def build_execution_context(
        self,
        account=None,
        connector=None,
        payload=None,
    ):
        """
        Creates execution context object.
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

            "payload":
                payload or {},

        }



    # -------------------------------------------------------------------------
    # Queue Helpers
    # -------------------------------------------------------------------------

    def enqueue_job(
        self,
        account,
        action,
        payload=None,
        priority="1",
    ):
        """
        Creates queue execution item.
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

            "priority":
                priority,

            "state":
                "pending",

        })



    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_statistics(self):
        """
        Returns SCE global statistics.
        """

        return {

            "plugins":
                self.env[
                    "sce.plugin"
                ].search_count([]),


            "connectors":
                self.env[
                    "sce.connector"
                ].search_count([]),


            "accounts":
                self.env[
                    "sce.account"
                ].search_count([]),


            "jobs":
                self.env[
                    "sce.job"
                ].search_count([]),


            "queue":
                self.env[
                    "sce.queue"
                ].search_count([]),


            "logs":
                self.env[
                    "sce.log"
                ].search_count([]),

        }



    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def cleanup(
        self,
        days=90,
    ):
        """
        Executes SCE cleanup tasks.
        """

        result = {}


        if "sce.log" in self.env:

            result["logs"] = (
                self.env[
                    "sce.log"
                ].cleanup_old_logs(
                    days
                )
            )


        return result



    # -------------------------------------------------------------------------
    # Version
    # -------------------------------------------------------------------------

    def version(self):
        """
        Returns SCE kernel version.
        """

        return "19.0.1.0.0"