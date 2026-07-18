# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.model
    def _sw_is_import_context(self):
        ctx = self.env.context
        return bool(
            ctx.get("import_file")
            or ctx.get("import_mode")
            or ctx.get("is_import")
            or ctx.get("from_import")
        )

    @api.model
    def _sw_find_template_by_reference(self, vals):
        """
        Intenta resolver product.template por:
        - default_code (si viene en columnas relacionadas)
        - nombre (fallback opcional)
        """
        ProductTmpl = self.env["product.template"]

        # posibles claves de import custom / externas
        code_candidates = [
            vals.get("product_default_code"),
            vals.get("default_code"),
            vals.get("x_product_code"),
        ]
        name_candidates = [
            vals.get("product_name"),
            vals.get("x_product_name"),
            vals.get("name"),
        ]

        for code in code_candidates:
            if code:
                rec = ProductTmpl.search([("default_code", "=", code)], limit=1)
                if rec:
                    return rec

        for name in name_candidates:
            if name:
                rec = ProductTmpl.search([("name", "=", name)], limit=1)
                if rec:
                    return rec

        return ProductTmpl.browse()

    @api.model
    def _sw_find_existing_supplierinfo(self, vals):
        """
        Busca supplierinfo existente por partner + product_code (código proveedor).
        """
        partner_id = vals.get("partner_id")
        product_code = vals.get("product_code")

        if not partner_id or not product_code:
            return self.browse()

        return self.search(
            [
                ("partner_id", "=", partner_id),
                ("product_code", "=", product_code),
            ],
            limit=1,
        )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Regla solicitada para importación:
        - Buscar supplierinfo por código proveedor y actualizar si existe.
        - Si no existe, intentar vincular product_tmpl por código/nombre.
        - Si no encuentra vinculación, NO crear nada para esa fila.
        """
        if not self._sw_is_import_context():
            return super().create(vals_list)

        result_records = self.browse()

        for vals in vals_list:
            existing = self._sw_find_existing_supplierinfo(vals)
            if existing:
                _logger.info(
                    "[sw_import_code] supplierinfo import match by vendor code -> update id=%s",
                    existing.id,
                )
                existing.write(vals)
                result_records |= existing
                continue

            # Si ya viene product_tmpl_id explícito y válido, permitir create
            product_tmpl_id = vals.get("product_tmpl_id")
            if not product_tmpl_id:
                template = self._sw_find_template_by_reference(vals)
                if template:
                    vals["product_tmpl_id"] = template.id
                else:
                    _logger.warning(
                        "[sw_import_code] supplierinfo import skipped (no supplier match, no product template match). vals=%s",
                        vals,
                    )
                    continue

            result_records |= super(ProductSupplierInfo, self).create([vals])

        return result_records
