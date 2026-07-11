# -*- coding: utf-8 -*-
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
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date()
    synced_products_count = fields.Integer(default=0, tracking=True)
    over_limit = fields.Boolean(compute="_compute_over_limit", store=True)

    @api.depends("synced_products_count", "plan_id.max_synced_products")
    def _compute_over_limit(self):
        for rec in self:
            rec.over_limit = bool(rec.plan_id and rec.synced_products_count > rec.plan_id.max_synced_products)


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
            ("errors", "Errors"),
        ],
        required=True,
        index=True,
    )
    value = fields.Float(required=True, default=0.0)
    notes = fields.Char()