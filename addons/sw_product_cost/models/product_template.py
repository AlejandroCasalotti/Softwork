# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Extension of product.template for advanced cost management.
    """

    _inherit = "product.template"

    # ---------------------------------------------------------
    # Cost information
    # ---------------------------------------------------------

    sw_cost_amount = fields.Float(
        string="Calculated Cost",
        compute="_compute_sw_cost_amount",
        store=True,
        help="Calculated internal cost used for margin calculation.",
    )

    sw_cost_margin = fields.Float(
        string="Applied Margin (%)",
        compute="_compute_sw_cost_margin",
        store=True,
    )

    sw_cost_rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_rule",
        store=True,
    )

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_suggested_price",
        store=True,
    )

    # ---------------------------------------------------------
    # Compute cost
    # ---------------------------------------------------------

    @api.depends(
        "standard_price",
    )
    def _compute_sw_cost_amount(self):

        for product in self:
            product.sw_cost_amount = (
                product.standard_price or 0.0
            )

    # ---------------------------------------------------------
    # Find applicable rule
    # ---------------------------------------------------------

    def _get_sw_cost_rule(self):

        self.ensure_one()

        Rule = self.env["sw.product.cost.rule"]

        domain = [
            ("active", "=", True),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]

        rules = Rule.search(
            domain,
            order="sequence asc",
        )

        for rule in rules:

            if rule.rule_type == "product":

                if rule.product_id == self:
                    return rule


            elif rule.rule_type == "category":

                if rule.categ_id == self.categ_id:
                    return rule


            elif rule.rule_type == "brand":

                if (
                    hasattr(self, "brand_id")
                    and rule.brand_id == self.brand_id
                ):
                    return rule


            elif rule.rule_type == "global":

                return rule


        return False


    # ---------------------------------------------------------
    # Compute applied rule
    # ---------------------------------------------------------

    @api.depends(
        "company_id",
        "categ_id",
    )
    def _compute_sw_cost_rule(self):

        for product in self:

            rule = product._get_sw_cost_rule()

            product.sw_cost_rule_id = (
                rule.id if rule else False
            )


    # ---------------------------------------------------------
    # Compute margin
    # ---------------------------------------------------------

    @api.depends(
        "sw_cost_rule_id",
    )
    def _compute_sw_cost_margin(self):

        for product in self:

            if product.sw_cost_rule_id:

                product.sw_cost_margin = (
                    product.sw_cost_rule_id.margin_value
                    or 0.0
                )

            else:

                product.sw_cost_margin = 0.0


    # ---------------------------------------------------------
    # Compute suggested price
    # ---------------------------------------------------------

    @api.depends(
        "sw_cost_amount",
        "sw_cost_rule_id",
    )
    def _compute_sw_suggested_price(self):

        for product in self:

            if product.sw_cost_rule_id:

                product.sw_suggested_price = (
                    product.sw_cost_rule_id
                    .calculate_sale_price(
                        product.sw_cost_amount
                    )
                )

            else:

                product.sw_suggested_price = (
                    product.sw_cost_amount
                )