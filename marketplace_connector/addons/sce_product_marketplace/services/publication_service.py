# -*- coding: utf-8 -*-
import json

from odoo import fields, models
from odoo.exceptions import UserError


class MarketplacePublicationService(models.AbstractModel):
    _name = "marketplace.publication.service"
    _description = "Servicio genérico de publicaciones en marketplaces"

    def _build_payload(self, publication):
        def load_json(value, default):
            if not value:
                return default
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError) as err:
                raise UserError(
                    "Los datos JSON de la publicación '%s' no son válidos: %s"
                    % (publication.display_name, err)
                ) from err
            return parsed

        return {
            "publication_id": publication.id,
            "product_tmpl_id": publication.product_tmpl_id.id,
            "account_id": publication.account_id.id,
            "external_id": publication.external_id or False,
            "title": publication.title or publication.product_tmpl_id.name,
            "category_id": publication.category_ref or False,
            "listing_type": publication.listing_type or False,
            "condition": publication.condition or "new",
            "shipping_mode": publication.shipping_mode or False,
            "price": publication.price,
            "stock": publication.effective_qty,
            "attributes": load_json(publication.attributes_json, []),
            "pictures": load_json(publication.pictures_json, []),
            "sale_terms": load_json(publication.sale_terms_json, []),
            "provider_data": load_json(publication.provider_data_json, {}),
        }

    def _get_provider(self, publication):
        if not publication.account_id:
            raise UserError("La publicación necesita una cuenta de marketplace.")
        return self.env["sce.provider.factory"].get_provider(publication.account_id)

    def publish(self, publication):
        publication.ensure_one()
        publication._validate_for_operation()
        payload = self._build_payload(publication)
        publication.write({"state": "publishing", "error_message": False})
        try:
            result = self._get_provider(publication).publish_product(payload) or {}
            publication._apply_provider_result(result, published=True)
            return result
        except Exception as err:
            publication.write({"state": "failed", "error_message": str(err)})
            raise

    def update(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede actualizar una publicación sin ID externo.")
        payload = self._build_payload(publication)
        try:
            result = self._get_provider(publication).update_product(payload) or {}
            publication._apply_provider_result(result)
            return result
        except Exception as err:
            publication.write({"state": "failed", "error_message": str(err)})
            raise

    def update_stock(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede sincronizar stock sin ID externo.")
        result = self._get_provider(publication).update_stock(self._build_payload(publication)) or {}
        publication.write({"sync_date": fields.Datetime.now()})
        return result

    def update_price(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede sincronizar precio sin ID externo.")
        result = self._get_provider(publication).update_price(self._build_payload(publication)) or {}
        publication.write({"sync_date": fields.Datetime.now()})
        return result

    def delete(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede eliminar una publicación sin ID externo.")
        result = self._get_provider(publication).delete_product(self._build_payload(publication)) or {}
        publication.write({"state": "draft", "external_id": False, "external_url": False})
        return result