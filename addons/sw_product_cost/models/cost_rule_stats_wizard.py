# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SWProductCostRuleStatsWizard(models.TransientModel):
    _name = "sw.product.cost.rule.stats.wizard"
    _description = "Cost Rule Products Stats"

    rule_id = fields.Many2one(
        "sw.product.cost.rule",
        string="Cost Rule",
        required=True,
        readonly=True,
    )
    product_count = fields.Integer(
        string="Products with this rule applied",
        compute="_compute_product_count",
        readonly=True,
    )
    product_ids = fields.Many2many(
        "product.template",
        string="Products",
        compute="_compute_product_ids",
        readonly=True,
    )

    @api.depends("rule_id")
    def _compute_product_count(self):
        Product = self.env["product.template"]
        for rec in self:
            rec.product_count = Product.search_count([("sw_cost_rule_id", "=", rec.rule_id.id)])

    @api.depends("rule_id")
    def _compute_product_ids(self):
        Product = self.env["product.template"]
        for rec in self:
            rec.product_ids = Product.search([("sw_cost_rule_id", "=", rec.rule_id.id)])

    def action_open_products(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Products with Rule Applied",
            "res_model": "product.template",
            "view_mode": "list,form",
            "domain": [("sw_cost_rule_id", "=", self.rule_id.id)],
            "context": {"search_default_filter_to_sell": 0},
        }