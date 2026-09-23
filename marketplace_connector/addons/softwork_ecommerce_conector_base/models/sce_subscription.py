# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import timedelta
import json

from dateutil.relativedelta import relativedelta

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
    max_monthly_orders = fields.Integer(required=True, default=100)
    price_monthly = fields.Monetary(required=True, default=0.0, currency_field="currency_id")
    portal_price_monthly = fields.Monetary(
        required=True, default=0.0, currency_field="currency_id"
    )
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
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict", tracking=True)
    customer_type = fields.Selection(
        [("premium", "Cliente Premium"), ("portal", "Cliente Portal")],
        default="portal",
        required=True,
        tracking=True,
    )
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
    trial_end_date = fields.Date(
        string="Fin del período de prueba",
        default=lambda self: fields.Date.today() + timedelta(days=13),
        readonly=True,
    )
    end_date = fields.Date()
    synced_products_count = fields.Integer(default=0, tracking=True)
    synced_orders_count = fields.Integer(default=0, tracking=True)
    connected_accounts_count = fields.Integer(default=0, tracking=True)
    period_start = fields.Date(compute="_compute_current_period", store=True)
    period_end = fields.Date(compute="_compute_current_period", store=True)
    usage_summary_ids = fields.One2many("sce.usage.summary", "subscription_id")
    sale_order_ids = fields.One2many("sale.order", "sce_subscription_id")
    last_billed_period_end = fields.Date(readonly=True)
    last_sale_order_id = fields.Many2one("sale.order", readonly=True)
    over_limit = fields.Boolean(compute="_compute_over_limit", store=True)

    @api.depends("synced_products_count", "plan_id.max_synced_products")
    def _compute_over_limit(self):
        for rec in self:
            rec.over_limit = bool(rec.plan_id and rec.synced_products_count > rec.plan_id.max_synced_products)

    @api.depends("start_date", "end_date")
    def _compute_current_period(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.start_date:
                rec.period_start = rec.period_end = False
                continue
            start = rec.start_date
            while start > today:
                start -= relativedelta(months=1)
            period_end = start + relativedelta(months=1) - timedelta(days=1)
            while period_end < today:
                start = start + relativedelta(months=1)
                period_end = start + relativedelta(months=1) - timedelta(days=1)
            rec.period_start = start
            rec.period_end = period_end

    def _period_for_date(self, date_value):
        self.ensure_one()
        start = self.start_date
        while start + relativedelta(months=1) - timedelta(days=1) < date_value:
            start += relativedelta(months=1)
        return start, start + relativedelta(months=1) - timedelta(days=1)

    def _monthly_price(self):
        self.ensure_one()
        return self.plan_id.portal_price_monthly if self.customer_type == "portal" else self.plan_id.price_monthly

    @api.model
    def get_or_create_portal_subscription(self, partner):
        partner = partner.commercial_partner_id
        subscription = self.search(
            [("partner_id", "=", partner.id), ("state", "!=", "cancelled")],
            order="create_date desc",
            limit=1,
        )
        if subscription:
            if subscription.state == "trial" and not subscription.trial_end_date:
                subscription.trial_end_date = subscription.start_date + timedelta(days=13)
            return subscription
        plan = self.env.ref(
            "softwork_ecommerce_conector_base.sce_subscription_plan_initial", raise_if_not_found=False
        )
        if not plan:
            plan = self.env["sce.subscription.plan"].search([("active", "=", True)], order="sequence", limit=1)
        if not plan:
            return self.env["sce.subscription"]
        return self.create(
            {
                "name": f"SCE - {partner.name}",
                "company_id": self.env.company.id,
                "partner_id": partner.id,
                "plan_id": plan.id,
                "customer_type": "portal",
                "state": "trial",
                "start_date": fields.Date.today(),
                "trial_end_date": fields.Date.today() + timedelta(days=13),
            }
        )

    def _usage_for_period(self, start, end):
        self.ensure_one()
        metrics = self.env["sce.usage.metric"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("date", ">=", start),
                ("date", "<=", end),
                ("metric_type", "in", ["orders_imported", "products_synced"]),
            ],
            ["metric_type", "value:sum"],
            ["metric_type"],
        )
        totals = {row["metric_type"]: row["value"] for row in metrics}
        account_domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "connected"),
            ("active", "=", True),
        ]
        publication_count = self.env["marketplace.publication"].search_count(
            [("account_id.company_id", "=", self.company_id.id), ("state", "=", "published")]
        ) if "marketplace.publication" in self.env else 0
        return {
            "orders": int(totals.get("orders_imported", 0)),
            "products": publication_count or int(totals.get("products_synced", 0)),
            "accounts": self.env["sce.account"].search_count(account_domain),
        }

    def _select_plan_for_usage(self, usage):
        plans = self.env["sce.subscription.plan"].search(
            [("active", "=", True)], order="price_monthly asc, sequence asc"
        )
        for plan in plans:
            if usage["orders"] <= plan.max_monthly_orders and usage["products"] <= plan.max_synced_products:
                return plan
        return plans[-1] if plans else self.plan_id

    def _ensure_billing_product(self):
        product = self.env["product.product"].search(
            [("default_code", "=", "SCE-SUBSCRIPTION")], limit=1
        )
        if product:
            return product
        template = self.env["product.template"].create(
            {
                "name": "SCE Suscripción de integración",
                "default_code": "SCE-SUBSCRIPTION",
                "type": "service",
                "sale_ok": True,
                "purchase_ok": False,
            }
        )
        return template.product_variant_id

    def _create_draft_sale_order(self, start, end, usage, plan, amount):
        self.ensure_one()
        existing = self.env["sale.order"].search(
            [("sce_subscription_id", "=", self.id), ("sce_period_end", "=", end)], limit=1
        )
        if existing:
            return existing
        product = self._ensure_billing_product()
        days_total = (end - start).days + 1
        billable_start = start
        if self.trial_end_date and self.trial_end_date >= start:
            billable_start = min(end + timedelta(days=1), self.trial_end_date + timedelta(days=1))
        active_days = max(0, (end - billable_start).days + 1)
        amount_company_currency = self.plan_id.currency_id._convert(
            amount, self.company_id.currency_id, self.company_id, end
        )
        prorated_amount = amount_company_currency * active_days / days_total
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_id.id,
                "company_id": self.company_id.id,
                "origin": f"SCE {self.name} {start} - {end}",
                "sce_subscription_id": self.id,
                "sce_period_start": start,
                "sce_period_end": end,
                "sce_usage_json": json.dumps(usage, ensure_ascii=False),
                "order_line": [(0, 0, {
                    "product_id": product.id,
                    "name": f"SCE {plan.name} - {start} a {end}",
                    "product_uom_qty": 1.0,
                    "price_unit": prorated_amount,
                })],
            }
        )
        self.write({"last_billed_period_end": end, "last_sale_order_id": order.id})
        return order

    @api.model
    def cron_generate_usage_orders(self):
        today = fields.Date.today()
        for subscription in self.search([("state", "in", ["trial", "active", "grace", "restricted"])]):
            start, end = subscription._period_for_date(today - relativedelta(months=1))
            if end >= today or subscription.last_billed_period_end and subscription.last_billed_period_end >= end:
                continue
            usage = subscription._usage_for_period(start, end)
            plan = subscription._select_plan_for_usage(usage)
            order = subscription._create_draft_sale_order(
                start, end, usage, plan, plan.portal_price_monthly if subscription.customer_type == "portal" else plan.price_monthly
            )
            summary = self.env["sce.usage.summary"].search(
                [("subscription_id", "=", subscription.id), ("period_start", "=", start), ("period_end", "=", end)],
                limit=1,
            )
            values = {
                "subscription_id": subscription.id,
                "period_start": start,
                "period_end": end,
                "plan_id": plan.id,
                "orders_count": usage["orders"],
                "products_count": usage["products"],
                "connected_accounts_count": usage["accounts"],
                "days_active": (end - start).days + 1,
                "amount_usd": plan.portal_price_monthly if subscription.customer_type == "portal" else plan.price_monthly,
                "amount_company_currency": order.amount_total,
                "sale_order_id": order.id,
                "state": "ordered",
            }
            if summary:
                summary.write(values)
            else:
                self.env["sce.usage.summary"].create(values)

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
            if sub.state == "trial":
                if sub.trial_end_date and today <= sub.trial_end_date:
                    updates["state"] = "trial"
                else:
                    account_ready = bool(self.env["sce.account"].sudo().search_count(
                        [("company_id", "=", sub.company_id.id), ("initial_sync_queued", "=", True)]
                    ))
                    updates["state"] = "active" if account_ready else "restricted"
            elif sub.billing_status == "unpaid":
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