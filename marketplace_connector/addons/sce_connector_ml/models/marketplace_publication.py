# -*- coding: utf-8 -*-
import json

from odoo import models
from odoo.exceptions import UserError


class MarketplacePublication(models.Model):
    _inherit = "marketplace.publication"

    def check_ready_to_publish(self):
        self.ensure_one()
        errors = super().check_ready_to_publish()
        if errors or self.provider_type != "mercadolibre":
            return errors

        try:
            attributes = json.loads(self.attributes_json or "[]")
        except (TypeError, ValueError):
            return errors
        if not isinstance(attributes, list):
            return errors

        provider = self.env["sce.provider.factory"].get_provider(self.account_id)
        required_response = provider.get_category_required_fields(category_id=self.category_ref)
        required_items = required_response.get("items", []) if isinstance(required_response, dict) else []
        values_by_id = {
            item.get("id"): item
            for item in attributes
            if isinstance(item, dict) and item.get("id")
        }
        for item in required_items:
            if not isinstance(item, dict):
                continue
            attribute_id = item.get("id")
            value = values_by_id.get(attribute_id, {})
            if not (str(value.get("value_id") or "").strip() or str(value.get("value_name") or "").strip()):
                errors.append("Completa el atributo requerido: %s." % (item.get("name") or attribute_id))

        metadata_response = provider.get_category_attributes(category_id=self.category_ref)
        metadata = metadata_response.get("items", []) if isinstance(metadata_response, dict) else []
        seller_sku = next(
            (item for item in metadata if isinstance(item, dict) and item.get("id") == "SELLER_SKU"),
            None,
        )
        variants = self.product_tmpl_id.product_variant_ids.filtered("active")
        if seller_sku and seller_sku.get("required"):
            if len(variants) == 1 and not variants[0].default_code:
                errors.append("El producto no tiene SKU de vendedor.")
            elif len(variants) > 1 and seller_sku.get("allow_variations"):
                missing_sku = next((variant for variant in variants if not variant.default_code), None)
                if missing_sku:
                    errors.append("La variante %s no tiene SKU de vendedor." % missing_sku.display_name)
        return errors

    def action_publish(self):
        self.ensure_one()
        if self.provider_type == "mercadolibre" and not self.external_id:
            return self.action_open_ml_publish_assistant()
        return super().action_publish()

    def action_open_ml_publish_assistant(self):
        self.ensure_one()
        if self.provider_type != "mercadolibre":
            raise UserError("Este asistente aplica solo a publicaciones de MercadoLibre.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.assistant.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.product_tmpl_id.id,
                "default_publication_id": self.id,
                "default_step": "base",
            },
        }