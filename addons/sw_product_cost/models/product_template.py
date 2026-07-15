# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"


    sw_cost_rule_id = fields.Many2one(
        "sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_base_cost = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_final_cost = fields.Float(
        string="Final Calculated Cost",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    def _get_sw_cost_rule(self):

        self.ensure_one()

        Rule = self.env["sw.product.cost.rule"]

        rules = Rule.search(
            [
                ("active", "=", True),
                "|",
                ("company_id", "=", self.env.company.id),
                ("company_id", "=", False),
            ],
            order="sequence asc",
        )


        for rule in rules:

            if rule.rule_type == "global":
                return rule


            if rule.rule_type == "product":
                if rule.product_id == self:
                    return rule


            if rule.rule_type == "category":
                if rule.categ_id == self.categ_id:
                    return rule


            if rule.rule_type == "brand":

                if hasattr(self, "brand_id"):

                    if rule.brand_id == self.brand_id:
                        return rule


        return False



    @api.depends(
        "standard_price",
        "categ_id",
        "sw_cost_rule_id.line_ids.sequence",
        "sw_cost_rule_id.line_ids.operation",
        "sw_cost_rule_id.line_ids.value",
    )
    def _compute_sw_cost_values(self):

        for product in self:


            rule = product._get_sw_cost_rule()

            product.sw_cost_rule_id = rule


            base = product.standard_price


            product.sw_base_cost = base


            if rule:

                product.sw_final_cost = (
                    rule.calculate_cost(base)
                )


                product.sw_suggested_price = (
                    rule.calculate_sale_price(
                        product.sw_final_cost
                    )
                )


            else:

                product.sw_final_cost = base

                product.sw_suggested_price = base