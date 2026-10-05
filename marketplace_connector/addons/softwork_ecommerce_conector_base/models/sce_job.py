# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import fields, models


class SceJob(models.Model):
    _name = "sce.job"
    _description = "SCE Synchronization Job"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True)
    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", tracking=True, index=True)
    connector_id = fields.Many2one(related="account_id.connector_id", store=True, index=True)
    company_id = fields.Many2one(related="account_id.company_id", store=True, index=True)
    job_type = fields.Selection(
        selection=[
            ("sync_products", "Sync Products"),
            ("sync_stock", "Sync Stock"),
            ("sync_prices", "Sync Prices"),
            ("import_orders", "Import Orders"),
            ("sync_messages", "Sync Messages"),
            ("health_check", "Health Check"),
        ],
        required=True,
        default="sync_products",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("queued", "Queued"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="queued",
        required=True,
        tracking=True,
    )
    attempts = fields.Integer(default=0, tracking=True)
    max_retries = fields.Integer(default=3)
    started_at = fields.Datetime(tracking=True)
    finished_at = fields.Datetime(tracking=True)
    duration_ms = fields.Integer()
    payload_json = fields.Text()
    result_json = fields.Text()
    error_message = fields.Text()

    def action_enqueue(self):
        for rec in self:
            rec.write({"state": "queued", "error_message": False})
        return True

    def action_run_now(self):
        for rec in self:
            rec._execute_job()
        return True

    def _execute_job(self):
        self.ensure_one()
        if self.job_type != "health_check" and not self.account_id._sync_is_allowed():
            return
        start_dt = fields.Datetime.now()
        self.write({
            "state": "running",
            "started_at": start_dt,
            "finished_at": False,
            "duration_ms": 0,
            "error_message": False,
            "attempts": (self.attempts or 0) + 1,
        })

        event_model = self.env["sce.event"]
        log_service = self.env["sce.log.service"]
        metric_model = self.env["sce.usage.metric"]

        event_model.emit_event(
            name=f"Job started: {self.name}",
            event_type="JobStarted",
            connector=self.connector_id,
            account=self.account_id,
            job=self,
            payload={"job_type": self.job_type},
        )

        try:
            provider = self.env["sce.provider.factory"].get_provider(self.account_id)
            payload = {}
            if self.payload_json:
                try:
                    payload = json.loads(self.payload_json)
                except Exception:
                    payload = {"raw": self.payload_json}

            result = self._execute_provider_operation(provider, payload)
            if isinstance(result, dict) and (result.get("ok") is False or result.get("errors")):
                raise ValueError("La sincronización reportó errores; revisá los detalles del trabajo.")
            end_dt = fields.Datetime.now()
            duration = int((end_dt - start_dt).total_seconds() * 1000)

            self.write({
                "state": "done",
                "finished_at": end_dt,
                "duration_ms": duration,
                "result_json": json.dumps(result or {}),
                "error_message": False,
            })
            if self.job_type == "sync_products":
                for operation, enabled in (
                    ("sync_stock", self.account_id.sync_stock),
                    ("sync_prices", self.account_id.sync_prices),
                ):
                    if enabled and not self.search_count([
                        ("account_id", "=", self.account_id.id),
                        ("job_type", "=", operation), ("state", "in", ["queued", "running"]),
                    ]):
                        self.create({"name": f"{operation} - {self.account_id.name}",
                                     "account_id": self.account_id.id, "job_type": operation, "payload_json": "{}"})
            self.account_id.with_context(skip_initial_sync_check=True).write({"last_sync": end_dt})
            metric_model.create({
                "company_id": self.company_id.id,
                "connector_id": self.connector_id.id,
                "account_id": self.account_id.id,
                "metric_type": "jobs_done",
                "value": 1.0,
                "notes": f"Job {self.display_name} done",
            })
            metric_model.create({
                "company_id": self.company_id.id,
                "connector_id": self.connector_id.id,
                "account_id": self.account_id.id,
                "metric_type": "job_duration_avg_ms",
                "value": float(duration),
                "notes": f"Job {self.display_name} duration",
            })

            event_model.emit_event(
                name=f"Job finished: {self.name}",
                event_type="JobFinished",
                connector=self.connector_id,
                account=self.account_id,
                job=self,
                payload={"duration_ms": duration},
            )
            log_service.log(
                name="Job finished",
                message=f"Job {self.display_name} finished successfully",
                level="INFO",
                connector=self.connector_id,
                account=self.account_id,
                job=self,
                details_json=self.result_json,
            )
        except Exception as err:
            self._on_execution_failed(err)
            end_dt = fields.Datetime.now()
            duration = int((end_dt - start_dt).total_seconds() * 1000)
            self.write({
                "state": "failed",
                "finished_at": end_dt,
                "duration_ms": duration,
                "error_message": str(err),
            })
            metric_model.create({
                "company_id": self.company_id.id,
                "connector_id": self.connector_id.id,
                "account_id": self.account_id.id,
                "metric_type": "jobs_failed",
                "value": 1.0,
                "notes": f"Job {self.display_name} failed",
            })
            event_model.emit_event(
                name=f"Job failed: {self.name}",
                event_type="JobFailed",
                connector=self.connector_id,
                account=self.account_id,
                job=self,
                payload={"error": str(err)},
            )
            log_service.log(
                name="Job failed",
                message=f"Job {self.display_name} failed: {err}",
                level="ERROR",
                connector=self.connector_id,
                account=self.account_id,
                job=self,
                details_json=str(err),
            )

    def _on_execution_failed(self, error):
        """Hook for specialized jobs to synchronize domain error state."""
        return None

    def _execute_provider_operation(self, provider, payload):
        """Execute the default provider sync operation.

        Addons can override this hook for domain-specific job types without
        changing the queue lifecycle, metrics, events, or retry handling.
        """
        return provider.sync({"operation": self.job_type, "payload": payload})

    def cron_process_queue(self):
        jobs = self.search([("state", "=", "queued")], limit=50, order="create_date asc")
        for job in jobs:
            job._execute_job()

    def cron_retry_failed_jobs(self):
        jobs = self.search([("state", "=", "failed")], limit=50, order="write_date asc")
        for job in jobs:
            if (job.attempts or 0) < (job.max_retries or 0):
                job.write({"state": "queued", "error_message": False})

    def cron_cleanup_old_jobs(self):
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_jobs = self.search(
            [
                ("create_date", "<", cutoff),
                ("state", "in", ["done", "failed", "cancelled"]),
            ]
        )
        old_jobs.unlink()