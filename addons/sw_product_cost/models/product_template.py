# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Extension of product.template for advanced
    cost calculation and pricing rules.
    """

    _inherit = "product.template"


    # ---------------------------------------------------------
    # Applied rule
    # ---------------------------------------------------------

    sw_cost_rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_rule",
        store=True,
    )


    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_cost_amount = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Final calculated cost
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Calculated Final Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Final cost after applying cascade rules.",
    )


    # ---------------------------------------------------------
    # Margin
    # ---------------------------------------------------------

    sw_cost_margin = fields.Float(
        string="Applied Margin (%)",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Suggested sale price
    # ---------------------------------------------------------

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # =========================================================
    # Find applicable rule
    # =========================================================

    def _get_sw_cost_rule(self):

        self.ensure_one()

        Rule = self.env["sw.product.cost.rule"]


        rules = Rule.search(
            [
                ("active", "=", True),
                (
                    "|",
                    ("company_id", "=", self.env.company.id),
                    ("company_id", "=", False),
                ),
            ],
            order="sequence asc",
        )


        for rule in rules:


            # Product rule
            if rule.rule_type == "product":

                if rule.product_id == self:
                    return rule


            # Category rule
            elif rule.rule_type == "category":

                if rule.categ_id == self.categ_id:
                    return rule


            # Brand rule
            elif rule.rule_type == "brand":

                if hasattr(self, "brand_id"):

                    if rule.brand_id == self.brand_id:
                        return rule


            # Global rule
            elif rule.rule_type == "global":

                return rule


        return False


    # =========================================================
    # Compute rule
    # =========================================================

    @api.depends(
        "standard_price",
        "categ_id",
    )
    def _compute_sw_cost_rule(self):

        for product in self:

            product.sw_cost_rule_id = (
                product._get_sw_cost_rule()
            )


    # =========================================================
    # Calculate values
    # =========================================================

    @api.depends(
        "standard_price",
        "sw_cost_rule_id",
        "sw_cost_rule_id.margin_type",
        "sw_cost_rule_id.margin_value",
        "sw_cost_rule_id.line_ids",
    )
    def _compute_sw_cost_values(self):

        for product in self:


            base_cost = product.standard_price or 0.0


            product.sw_cost_amount = base_cost


            final_cost = base_cost


            margin = 0.0


            rule = product.sw_cost_rule_id


            if rule:


                # ---------------------------------------------
                # Apply cascade lines
                # ---------------------------------------------

                for line in rule.line_ids.sorted(
                    key=lambda x: x.sequence
                ):

                    final_cost = line.apply(final_cost)


                # ---------------------------------------------
                # Apply margin
                # ---------------------------------------------

                margin = rule.margin_value


                if rule.margin_type == "percentage":

                    percentage = (
                        rule.margin_value / 100
                    )


                    if percentage < 1:

                        final_cost = (
                            final_cost /
                            (1 - percentage)
                        )


                elif rule.margin_type == "fixed":

                    final_cost += (
                        rule.margin_value
                    )


            product.sw_final_cost = final_cost


            product.sw_cost_margin = margin


            product.sw_suggested_price = final_cost