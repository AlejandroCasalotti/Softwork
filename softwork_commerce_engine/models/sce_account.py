# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SceAccount(models.Model):
    _name = "sce.account"
    _description = "SCE Connector Account"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    connector_id = fields.Many2one("sce.connector", required=True, ondelete="restrict", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("connected", "Connected"),
            ("error", "Error"),
            ("disabled", "Disabled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    external_account_ref = fields.Char(string="External Account Reference", index=True)
    credentials_json = fields.Text(string="Credentials JSON")
    last_connection_check = fields.Datetime()
    last_error = fields.Text()
    job_ids = fields.One2many("sce.job", "account_id", string="Jobs")
    jobs_done_count = fields.Integer(compute="_compute_job_metrics")
    jobs_failed_count = fields.Integer(compute="_compute_job_metrics")
    avg_duration_ms = fields.Float(compute="_compute_job_metrics")

    @api.depends("job_ids.state", "job_ids.duration_ms")
    def _compute_job_metrics(self):
        for rec in self:
            done_jobs = rec.job_ids.filtered(lambda j: j.state == "done")
            failed_jobs = rec.job_ids.filtered(lambda j: j.state == "failed")
            rec.jobs_done_count = len(done_jobs)
            rec.jobs_failed_count = len(failed_jobs)
            rec.avg_duration_ms = (sum(done_jobs.mapped("duration_ms")) / len(done_jobs)) if done_jobs else 0.0

    def cron_health_check(self):
        accounts = self.search([("active", "=", True)])
        log_service = self.env["sce.log.service"]
        for acc in accounts:
            try:
                acc.last_connection_check = fields.Datetime.now()
                if acc.state not in ("connected", "draft"):
                    acc.state = "connected"
                if acc.last_error:
                    acc.last_error = False
                log_service.log(
                    name="Health check ok",
                    message=f"Health check OK for account {acc.display_name}",
                    level="INFO",
                    account=acc,
                    connector=acc.connector_id,
                )
            except Exception as err:
                acc.state = "error"
                acc.last_error = str(err)
                log_service.log(
                    name="Health check error",
                    message=f"Health check error for account {acc.display_name}: {err}",
                    level="ERROR",
                    account=acc,
                    connector=acc.connector_id,
                )