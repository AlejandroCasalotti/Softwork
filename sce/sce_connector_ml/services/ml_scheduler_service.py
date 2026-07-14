# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Scheduler Service
"""

from __future__ import annotations

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MLSchedulerService(models.AbstractModel):
    """
    Mercado Libre synchronization scheduler.

    Responsible for deciding WHAT should be
    synchronized and WHEN.
    """

    _name = "sce.ml.scheduler.service"
    _description = "Mercado Libre Scheduler Service"

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _sync_service(self):

        return self.env[
            "sce.ml.sync.service"
        ]


    def _kernel(self):

        return self.env[
            "sce.kernel"
        ]


    def _log(
        self,
        account,
        level,
        message,
    ):

        self.env[
            "sce.log"
        ].create_log(

            level=level,

            message=message,

            account_id=account.id,

            connector_id=account.connector_id.id,

            plugin_id=account.plugin_id.id,

            category="synchronization",

        )

    # ---------------------------------------------------------
    # Account Selection
    # ---------------------------------------------------------

    def get_accounts(self):
        """
        Returns accounts eligible
        for synchronization.
        """

        return self.env[
            "sce.account"
        ].search([

            ("active", "=", True),

            ("state", "=", "connected"),

            ("auto_sync", "=", True),

        ])

    # ---------------------------------------------------------
    # Synchronization Decision
    # ---------------------------------------------------------

    def should_synchronize(
        self,
        account,
    ):
        """
        Determines if account should
        be synchronized now.
        """

        if not account.last_sync:

            return True

        now = fields.Datetime.now()

        elapsed = (
            now -
            account.last_sync
        ).total_seconds()

        return (

            elapsed >=

            account.sync_interval * 60

        )

    # ---------------------------------------------------------
    # Queue Creation
    # ---------------------------------------------------------

    def schedule_account(
        self,
        account,
    ):
        """
        Creates synchronization job.
        """

        self._log(

            account,

            "info",

            "Scheduling synchronization.",

        )

        kernel = self._kernel()

        job = kernel.create_job(

            account,

            "synchronize",

        )

        queue = kernel.enqueue(

            account,

            "synchronize",

        )

        return {

            "job": job,

            "queue": queue,

        }

    # ---------------------------------------------------------
    # Scheduler
    # ---------------------------------------------------------

    def schedule(self):
        """
        Main scheduler.
        """

        accounts = self.get_accounts()

        scheduled = []

        for account in accounts:

            if not self.should_synchronize(
                account
            ):
                continue

            scheduled.append(

                self.schedule_account(
                    account
                )

            )

        return scheduled

    # ---------------------------------------------------------
    # Immediate Synchronization
    # ---------------------------------------------------------

    def run_now(
        self,
        account,
    ):
        """
        Executes synchronization immediately.
        """

        self._log(
            account,
            "info",
            "Manual synchronization started.",
        )

        return self._sync_service().synchronize(
            account
        )

    # ---------------------------------------------------------
    # Incremental Synchronization
    # ---------------------------------------------------------

    def run_incremental(
        self,
        account,
    ):
        """
        Executes incremental synchronization.
        """

        self._log(
            account,
            "info",
            "Incremental synchronization started.",
        )

        return self._sync_service().synchronize_incremental(
            account
        )

    # ---------------------------------------------------------
    # Priority Calculation
    # ---------------------------------------------------------

    def calculate_priority(
        self,
        account,
    ):
        """
        Calculates queue priority.

        Returns:
            0 = Low
            1 = Normal
            2 = High
            3 = Critical
        """

        if account.last_sync_status == "error":
            return "3"

        if not account.last_sync:
            return "2"

        return "1"

    # ---------------------------------------------------------
    # Queue Maintenance
    # ---------------------------------------------------------

    def cleanup_queue(self):
        """
        Removes cancelled and completed
        queue items older than 30 days.
        """

        limit_date = fields.Datetime.subtract(
            fields.Datetime.now(),
            days=30,
        )

        records = self.env[
            "sce.queue"
        ].search([

            (
                "state",
                "in",
                (
                    "done",
                    "cancelled",
                ),
            ),

            (
                "finished_at",
                "<",
                limit_date,
            ),

        ])

        count = len(records)

        records.unlink()

        return count

    # ---------------------------------------------------------
    # Retry Failed Jobs
    # ---------------------------------------------------------

    def retry_failed(self):
        """
        Retries failed jobs.
        """

        jobs = self.env[
            "sce.job"
        ].search([

            (
                "state",
                "=",
                "failed",
            ),

        ])

        retried = 0

        for job in jobs:

            try:

                job.retry()

                retried += 1

            except Exception as error:

                _logger.exception(error)

        return retried

    # ---------------------------------------------------------
    # Scheduler Statistics
    # ---------------------------------------------------------

    def statistics(self):
        """
        Returns scheduler statistics.
        """

        Account = self.env["sce.account"]

        Job = self.env["sce.job"]

        Queue = self.env["sce.queue"]

        return {

            "accounts":

                Account.search_count([

                    ("state", "=", "connected"),

                ]),

            "pending_jobs":

                Job.search_count([

                    ("state", "=", "pending"),

                ]),

            "running_jobs":

                Job.search_count([

                    ("state", "=", "running"),

                ]),

            "pending_queue":

                Queue.search_count([

                    ("state", "=", "pending"),

                ]),

            "processing_queue":

                Queue.search_count([

                    ("state", "=", "processing"),

                ]),

        }

    # ---------------------------------------------------------
    # Scheduler Health
    # ---------------------------------------------------------

    def health(self):
        """
        Returns scheduler health.
        """

        stats = self.statistics()

        healthy = (

            stats["pending_queue"] < 500

            and

            stats["running_jobs"] < 100

        )

        return {

            "healthy": healthy,

            "statistics": stats,

        }

    # ---------------------------------------------------------
    # Cron Entry Point
    # ---------------------------------------------------------

    def cron_scheduler(self):
        """
        Main cron entry point.
        """

        scheduled = self.schedule()

        self.retry_failed()

        return {

            "scheduled":

                len(scheduled),

            "health":

                self.health(),

        }