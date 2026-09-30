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
        if self.account_id.sync_paused:
            self.write(
                {
                    "state": "cancelled",
                    "finished_at": fields.Datetime.now(),
                    "error_message": "Sincronización pausada para esta cuenta.",
                }
            )
            self.account_id._update_initial_sync_status()
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
            result_summary = self._summarize_result(result or {})
            end_dt = fields.Datetime.now()
            duration = int((end_dt - start_dt).total_seconds() * 1000)

            self.write({
                "state": "done",
                "finished_at": end_dt,
                "duration_ms": duration,
                "result_json": json.dumps(result_summary),
                "payload_json": False,
                "error_message": False,
            })
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
                details_json=json.dumps(result_summary),
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
            self.account_id.with_context(skip_initial_sync_check=True).write(
                {
                    "last_error": (
                        f"Falló la sincronización «{self.name}» ({type(err).__name__}). "
                        "Podés reintentarla desde esta cuenta."
                    )
                }
            )
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
                payload={"error_type": type(err).__name__},
            )
            log_service.log(
                name="Job failed",
                message=f"Job {self.display_name} failed ({type(err).__name__})",
                level="ERROR",
                connector=self.connector_id,
                account=self.account_id,
                job=self,
                details_json=json.dumps({"error_type": type(err).__name__}),
            )
        self.account_id._update_initial_sync_status()
        if self.state == "done" and (self.account_id.last_error or "").startswith(
            "Falló la sincronización"
        ):
            remaining_failures = self.search_count(
                [("account_id", "=", self.account_id.id), ("state", "=", "failed")]
            )
            if not remaining_failures:
                self.account_id.with_context(skip_initial_sync_check=True).write(
                    {"last_error": False}
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

    def _summarize_result(self, result):
        if not isinstance(result, dict):
            return {"ok": bool(result)}
        allowed = (
            "ok",
            "action",
            "provider",
            "imported",
            "reconciled",
            "total_items",
            "updated_count",
            "total_mappings",
            "created",
            "state",
            "error_count",
            "unresolved_count",
            "next_offset",
            "complete",
            "truncated",
        )
        summary = {key: result[key] for key in allowed if key in result}
        if isinstance(result.get("errors"), list):
            summary["error_count"] = len(result["errors"])
        return summary

    def cron_process_queue(self):
        self.env.cr.execute(
            f"SELECT id FROM {self._table} "
            "WHERE state = %s ORDER BY create_date, id LIMIT 50 FOR UPDATE SKIP LOCKED",
            ("queued",),
        )
        jobs = self.browse([row[0] for row in self.env.cr.fetchall()])
        for job in jobs:
            job._execute_job()

    def cron_retry_failed_jobs(self):
        self.env.cr.execute(
            f"SELECT id FROM {self._table} "
            "WHERE state = %s ORDER BY write_date, id LIMIT 50 FOR UPDATE SKIP LOCKED",
            ("failed",),
        )
        jobs = self.browse([row[0] for row in self.env.cr.fetchall()])
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