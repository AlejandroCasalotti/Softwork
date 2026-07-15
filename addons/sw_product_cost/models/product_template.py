# -*- coding: utf-8 -*-

from odoo import api, fields, models



class ProductTemplate(models.Model):

    _inherit = "product.template"


    sw_cost_rule_id = fields.Many2one(
        "sw.product.cost.rule",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_final_cost = fields.Float(
        string="Final Cost",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    @api.depends(
        "standard_price",
        "categ_id",
    )
    def _compute_sw_cost_values(self):

        Rule = self.env["sw.product.cost.rule"]

        for product in self:

            rule = Rule.get_applicable_rule(product)

            product.sw_cost_rule_id = rule


            cost = product.standard_price


            if rule:

                cost = rule.calculate_cost(cost)


            product.sw_final_cost = cost

            product.sw_suggested_price = cost