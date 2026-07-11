# -*- coding: utf-8 -*-
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
    started_at = fields.Datetime(tracking=True)
    finished_at = fields.Datetime(tracking=True)
    duration_ms = fields.Integer()
    payload_json = fields.Text()
    result_json = fields.Text()
    error_message = fields.Text()

    def cron_cleanup_old_jobs(self):
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_jobs = self.search(
            [
                ("create_date", "<", cutoff),
                ("state", "in", ["done", "failed", "cancelled"]),
            ]
        )
        old_jobs.unlink()