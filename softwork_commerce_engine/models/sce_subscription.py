# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class SceSubscriptionPlan(models.Model):
    _name = "sce.subscription.plan"
    _description = "SCE Subscription Plan"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    max_synced_products = fields.Integer(required=True, default=1000)
    price_monthly = fields.Monetary(required=True, default=0.0, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    description = fields.Text()


class SceSubscription(models.Model):
    _name = "sce.subscription"
    _description = "SCE Subscription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, default="Subscription", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    plan_id = fields.Many2one("sce.subscription.plan", required=True, ondelete="restrict", tracking=True)
    state = fields.Selection(
        selection=[
            ("trial", "Trial"),
            ("active", "Active"),
            ("grace", "Grace Period"),
            ("restricted", "Restricted"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
        ],
        default="trial",
        required=True,
        tracking=True,
    )
    billing_status = fields.Selection(
        selection=[
            ("current", "Current"),
            ("past_due", "Past Due"),
            ("unpaid", "Unpaid"),
        ],
        default="current",
        required=True,
        tracking=True,
    )
    grace_until = fields.Date(tracking=True)
    last_billing_check = fields.Datetime(readonly=True)
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date()
    synced_products_count = fields.Integer(default=0, tracking=True)
    over_limit = fields.Boolean(compute="_compute_over_limit", store=True)

    @api.depends("synced_products_count", "plan_id.max_synced_products")
    def _compute_over_limit(self):
        for rec in self:
            rec.over_limit = bool(rec.plan_id and rec.synced_products_count > rec.plan_id.max_synced_products)

    def action_mark_past_due(self):
        today = fields.Date.today()
        log_service = self.env["sce.log.service"]
        event_model = self.env["sce.event"]
        for rec in self:
            previous_state = rec.state
            rec.write({
                "billing_status": "past_due",
                "state": "grace" if rec.state not in ("suspended", "cancelled") else rec.state,
                "grace_until": today + timedelta(days=7),
            })
            event_model.emit_event(
                name=f"Subscription billing past due: {rec.display_name}",
                event_type="SubscriptionBillingPastDue",
                payload={"previous_state": previous_state, "new_state": rec.state},
                company=rec.company_id,
            )
            log_service.log(
                name="Subscription past due",
                message=f"Subscription {rec.display_name} marked as past due",
                level="WARNING",
            )
        return True

    def action_mark_unpaid(self):
        log_service = self.env["sce.log.service"]
        event_model = self.env["sce.event"]
        for rec in self:
            previous_state = rec.state
            rec.write({
                "billing_status": "unpaid",
                "state": "suspended" if rec.state != "cancelled" else "cancelled",
            })
            event_model.emit_event(
                name=f"Subscription billing unpaid: {rec.display_name}",
                event_type="SubscriptionBillingUnpaid",
                payload={"previous_state": previous_state, "new_state": rec.state},
                company=rec.company_id,
            )
            log_service.log(
                name="Subscription unpaid",
                message=f"Subscription {rec.display_name} marked as unpaid",
                level="ERROR",
            )
        return True

    def action_mark_current(self):
        log_service = self.env["sce.log.service"]
        event_model = self.env["sce.event"]
        for rec in self:
            previous_state = rec.state
            new_state = "active" if rec.state not in ("cancelled",) else "cancelled"
            rec.write({
                "billing_status": "current",
                "state": new_state,
                "grace_until": False,
            })
            event_model.emit_event(
                name=f"Subscription billing current: {rec.display_name}",
                event_type="SubscriptionBillingCurrent",
                payload={"previous_state": previous_state, "new_state": rec.state},
                company=rec.company_id,
            )
            log_service.log(
                name="Subscription current",
                message=f"Subscription {rec.display_name} marked as current",
                level="INFO",
            )
        return True

    @api.model
    def cron_billing_control(self):
        subs = self.search([("state", "not in", ["cancelled", "suspended"])])
        now_dt = fields.Datetime.now()
        today = fields.Date.today()
        log_service = self.env["sce.log.service"]
        event_model = self.env["sce.event"]
        for sub in subs:
            previous_state = sub.state
            updates = {"last_billing_check": now_dt}
            if sub.billing_status == "unpaid":
                updates["state"] = "suspended"
            elif sub.over_limit:
                updates["state"] = "restricted"
            elif sub.billing_status == "past_due":
                if sub.grace_until and sub.grace_until < today:
                    updates["state"] = "suspended"
                else:
                    updates["state"] = "grace"
            else:
                if sub.state not in ("cancelled",):
                    updates["state"] = "active"

            sub.write(updates)

            if sub.state != previous_state:
                event_model.emit_event(
                    name=f"Subscription state changed by billing cron: {sub.display_name}",
                    event_type="SubscriptionStateChanged",
                    payload={
                        "reason": "cron_billing_control",
                        "previous_state": previous_state,
                        "new_state": sub.state,
                        "billing_status": sub.billing_status,
                        "over_limit": bool(sub.over_limit),
                    },
                    company=sub.company_id,
                )
                log_service.log(
                    name="Subscription state changed",
                    message=(
                        f"Subscription {sub.display_name} changed state "
                        f"from {previous_state} to {sub.state} (billing cron)"
                    ),
                    level="WARNING" if sub.state in ("restricted", "suspended", "grace") else "INFO",
                )


class SceUsageMetric(models.Model):
    _name = "sce.usage.metric"
    _description = "SCE Usage Metric"
    _order = "date desc, id desc"

    date = fields.Date(required=True, default=fields.Date.context_today, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    connector_id = fields.Many2one("sce.connector", ondelete="set null", index=True)
    account_id = fields.Many2one("sce.account", ondelete="set null", index=True)
    metric_type = fields.Selection(
        selection=[
            ("products_synced", "Products Synced"),
            ("orders_imported", "Orders Imported"),
            ("stock_updates", "Stock Updates"),
            ("price_updates", "Price Updates"),
            ("messages_synced", "Messages Synced"),
            ("jobs_done", "Jobs Done"),
            ("jobs_failed", "Jobs Failed"),
            ("job_duration_avg_ms", "Job Avg Duration (ms)"),
            ("errors", "Errors"),
        ],
        required=True,
        index=True,
    )
    value = fields.Float(required=True, default=0.0)
    notes = fields.Char()