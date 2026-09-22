# -*- coding: utf-8 -*-
import json

from odoo import fields, models


class SceBillingSaleOrder(models.Model):
    _inherit = "sale.order"

    sce_subscription_id = fields.Many2one("sce.subscription", string="SCE Subscription", index=True)
    sce_period_start = fields.Date(string="SCE Period Start", index=True)
    sce_period_end = fields.Date(string="SCE Period End", index=True)
    sce_usage_json = fields.Text(string="SCE Usage Snapshot")

    def sce_usage_snapshot(self):
        self.ensure_one()
        try:
            return json.loads(self.sce_usage_json or "{}")
        except (TypeError, ValueError):
            return {}


class SceUsageSummary(models.Model):
    _name = "sce.usage.summary"
    _description = "SCE Usage Summary"
    _order = "period_start desc, id desc"

    subscription_id = fields.Many2one("sce.subscription", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="subscription_id.company_id", store=True, index=True)
    partner_id = fields.Many2one(related="subscription_id.partner_id", store=True, index=True)
    period_start = fields.Date(required=True, index=True)
    period_end = fields.Date(required=True, index=True)
    plan_id = fields.Many2one("sce.subscription.plan", required=True, ondelete="restrict")
    customer_type = fields.Selection(related="subscription_id.customer_type", store=True)
    orders_count = fields.Integer(default=0)
    products_count = fields.Integer(default=0)
    connected_accounts_count = fields.Integer(default=0)
    days_active = fields.Integer(default=0)
    amount_usd = fields.Monetary(currency_field="currency_id")
    amount_company_currency = fields.Monetary(currency_field="company_currency_id")
    currency_id = fields.Many2one(related="plan_id.currency_id", store=True, string="Moneda del plan")
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", store=True, string="Moneda de la empresa"
    )
    sale_order_id = fields.Many2one("sale.order", readonly=True, index=True)
    state = fields.Selection(
        [("calculated", "Calculated"), ("ordered", "Order Created")],
        default="calculated",
        required=True,
    )

    _sce_usage_summary_unique = models.Constraint(
        "UNIQUE(subscription_id, period_start, period_end)",
        "Ya existe un resumen para este período de suscripción.",
    )
