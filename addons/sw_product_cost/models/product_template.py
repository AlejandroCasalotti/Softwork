# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Product template extension for cascading cost rules.
    """

    _inherit = "product.template"


    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_cost_amount = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_amount",
        store=True,
    )


    # ---------------------------------------------------------
    # Applied rules
    # ---------------------------------------------------------

    sw_cost_rule_ids = fields.Many2many(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rules",
        compute="_compute_sw_cost_rules",
        store=True,
    )


    # ---------------------------------------------------------
    # Calculated values
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Calculated Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Cost after applying discounts and extra charges.",
    )


    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    sw_total_margin = fields.Float(
        string="Total Margin",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    @api.depends(
        "standard_price",
    )
    def _compute_sw_cost_amount(self):

        for product in self:

            product.sw_cost_amount = (
                product.standard_price
            )


    # ---------------------------------------------------------
    # Search applicable rules
    # ---------------------------------------------------------

    def _get_sw_cost_rules(self):

        self.ensure_one()


        Rule = self.env[
            "sw.product.cost.rule"
        ]


        rules = Rule.search(
            [
                ("active", "=", True),
                "|",
                (
                    "company_id",
                    "=",
                    self.env.company.id,
                ),
                (
                    "company_id",
                    "=",
                    False,
                ),
            ],
            order="sequence asc",
        )


        result = Rule.browse()


        for rule in rules:


            if rule.rule_type == "global":

                result |= rule



            elif rule.rule_type == "product":

                if rule.product_id == self:
                    result |= rule



            elif rule.rule_type == "category":

                if rule.categ_id == self.categ_id:
                    result |= rule



            elif rule.rule_type == "brand":


                if hasattr(self, "brand_id"):

                    if rule.brand_id == self.brand_id:
                        result |= rule


        return result



    # ---------------------------------------------------------
    # Compute rules
    # ---------------------------------------------------------

    @api.depends(
        "standard_price",
        "categ_id",
    )
    def _compute_sw_cost_rules(self):

        for product in self:

            product.sw_cost_rule_ids = (
                product._get_sw_cost_rules()
            )


    # ---------------------------------------------------------
    # Cascade calculation
    # ---------------------------------------------------------

    @api.depends(
        "sw_cost_amount",
        "sw_cost_rule_ids",
        "sw_cost_rule_ids.line_ids",
        "sw_cost_rule_ids.line_ids.value",
        "sw_cost_rule_ids.line_ids.operation",
    )
    def _compute_sw_cost_values(self):


        for product in self:


            amount = (
                product.sw_cost_amount
            )


            total_margin = 0



            rules = product.sw_cost_rule_ids.sorted(
                "sequence"
            )


            for rule in rules:


                lines = rule.line_ids.filtered(
                    lambda x: x.active
                ).sorted(
                    "sequence"
                )


                for line in lines:


                    amount = line.apply(
                        amount
                    )


                    if line.operation == "margin":

                        total_margin += (
                            line.value
                        )



            product.sw_final_cost = amount


            product.sw_suggested_price = amount


            product.sw_total_margin = (
                total_margin
            )



    # ---------------------------------------------------------
    # Manual recompute
    # ---------------------------------------------------------

    def action_recalculate_cost(self):

        for product in self:

            product._compute_sw_cost_values()

        return True