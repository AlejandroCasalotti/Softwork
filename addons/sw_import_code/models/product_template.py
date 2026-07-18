# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _sw_is_import_context(self):
        """Heurística flexible para detectar contexto de importación."""
        ctx = self.env.context
        return bool(
            ctx.get("import_file")
            or ctx.get("import_mode")
            or ctx.get("is_import")
            or ctx.get("from_import")
        )

    @api.model
    def _sw_find_template_by_code_or_name(self, vals):
        """
        Busca product.template por:
        1) default_code
        2) name
        """
        Product = self.env["product.template"]

        default_code = vals.get("default_code")
        name = vals.get("name")

        if default_code:
            rec = Product.search([("default_code", "=", default_code)], limit=1)
            if rec:
                return rec

        if name:
            rec = Product.search([("name", "=", name)], limit=1)
            if rec:
                return rec

        return Product.browse()

    @api.model_create_multi
    def create(self, vals_list):
        """
        En importación:
        - Si encuentra por default_code o name, actualiza en vez de crear.
        - Si no encuentra, crea nuevo.
        """
        if not self._sw_is_import_context():
            return super().create(vals_list)

        created_records = self.browse()
        for vals in vals_list:
            existing = self._sw_find_template_by_code_or_name(vals)
            if existing:
                _logger.info(
                    "[sw_import_code] product.template import match -> update id=%s",
                    existing.id,
                )
                existing.write(vals)
                created_records |= existing
            else:
                created_records |= super(ProductTemplate, self).create([vals])
        return created_records