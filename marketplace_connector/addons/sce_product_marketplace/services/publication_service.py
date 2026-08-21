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

        provider_data = load_json(publication.provider_data_json, {})
        if not isinstance(provider_data, dict):
            provider_data = {}

        payload = {
            "publication_id": publication.id,
            "product_tmpl_id": publication.product_tmpl_id.id,
            "account_id": publication.account_id.id,
            "external_id": publication.external_id or False,
            "status": publication.external_status or False,
            "title": publication.title or publication.product_tmpl_id.name,
            "category_id": publication.category_ref or False,
            "listing_type": publication.listing_type or False,
            "listing_type_id": publication.listing_type or False,
            "condition": publication.condition or "new",
            "shipping_mode": publication.shipping_mode or False,
            "price": publication.price,
            "stock": publication.effective_qty,
            "available_quantity": publication.effective_qty,
            "attributes": load_json(publication.attributes_json, []),
            "pictures": load_json(publication.pictures_json, []),
            "sale_terms": load_json(publication.sale_terms_json, []),
            "provider_data": provider_data,
        }
        payload.update(
            {
                "family_name": provider_data.get("family_name") or "",
                "description_html": provider_data.get("description_html") or "",
                "description_plain_text": provider_data.get("description_plain_text") or "",
                "warranty": provider_data.get("warranty") or "",
            }
        )
        return payload

    def _get_provider(self, publication):
        if not publication.account_id:
            raise UserError("La publicación necesita una cuenta de marketplace.")
        return self.env["sce.provider.factory"].get_provider(publication.account_id)

    def diagnose_account(self, account):
        if not account:
            raise UserError("La publicación necesita una cuenta de marketplace.")
        result = self.env["sce.provider.factory"].get_provider(account).health() or {}
        if not isinstance(result, dict):
            raise UserError("El provider devolvió una respuesta de diagnóstico inválida.")
        return result

    def validate_required_attributes(self, account, category_id, attributes):
        if not account or not category_id:
            return []
        response = self.env["sce.provider.factory"].get_provider(account).get_category_required_fields(
            category_id=category_id
        )
        required = response.get("items") if isinstance(response, dict) else []
        if not isinstance(required, list):
            return []
        attribute_map = {
            (attribute.get("id") or "").strip(): attribute
            for attribute in attributes
            if isinstance(attribute, dict) and (attribute.get("id") or "").strip()
        }
        issues = []
        for item in required:
            if not isinstance(item, dict):
                continue
            attribute_id = (item.get("id") or "").strip()
            current = attribute_map.get(attribute_id, {})
            if not (str(current.get("value_id") or "").strip() or str(current.get("value_name") or "").strip()):
                issues.append("Falta atributo requerido ML: %s" % attribute_id)
        return issues

    def enqueue(self, publication, operation):
        publication.ensure_one()
        job_types = {
            "publish": "publish_product",
            "update": "update_product",
            "update_stock": "sync_publication_stock",
            "update_price": "sync_publication_price",
            "delete": "delete_product",
            "sync": "sync_publication",
            "import_order": "import_order",
        }
        job_type = job_types.get(operation)
        if not job_type:
            raise UserError("Operación de publicación no soportada: %s" % operation)
        if operation == "publish":
            publication._validate_for_operation()
            publication.write({"state": "publishing", "error_message": False})
        elif not publication.external_id:
            raise UserError("La publicación necesita un ID externo para la operación '%s'." % operation)
        job = self.env["sce.job"].create(
            {
                "name": "%s - %s" % (operation.replace("_", " ").title(), publication.display_name),
                "account_id": publication.account_id.id,
                "job_type": job_type,
                "publication_id": publication.id,
                "payload_json": json.dumps({"publication_id": publication.id}),
            }
        )
        return job

    def handle_webhook(self, account, payload):
        if not account or not isinstance(payload, dict):
            return False
        resource = payload.get("resource") or ""
        topic = (payload.get("topic") or payload.get("type") or "").lower()
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        external_id = data.get("id") or payload.get("item_id") or payload.get("id")
        if "order" in topic or "/orders/" in resource:
            order_id = external_id
            if not order_id and isinstance(resource, str):
                parts = [part for part in resource.rstrip("/").split("/") if part]
                if "orders" in parts:
                    order_id = parts[parts.index("orders") + 1] if len(parts) > parts.index("orders") + 1 else False
            if order_id:
                return self.enqueue_order(account, str(order_id))
            return False
        if not external_id and isinstance(resource, str):
            parts = [part for part in resource.rstrip("/").split("/") if part]
            if parts:
                external_id = parts[-1]
        if not external_id:
            return False
        publication = self.env["marketplace.publication"].search(
            [("account_id", "=", account.id), ("external_id", "=", str(external_id))],
            limit=1,
        )
        if not publication:
            return False
        return self.enqueue(publication, "sync")

    def enqueue_order(self, account, external_id):
        if not account or not external_id:
            raise UserError("La importación necesita cuenta e ID externo de orden.")
        return self.env["sce.job"].create(
            {
                "name": "Import order %s" % external_id,
                "account_id": account.id,
                "job_type": "import_order",
                "external_id": str(external_id),
                "payload_json": json.dumps({"external_id": str(external_id)}),
            }
        )

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

    def sync_from_marketplace(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede sincronizar una publicación sin ID externo.")
        result = self._get_provider(publication).get_item(publication.external_id) or {}
        item = result.get("item") if isinstance(result, dict) else {}
        if not isinstance(item, dict):
            raise UserError("El marketplace devolvió un ítem inválido.")
        values = {"sync_date": fields.Datetime.now(), "error_message": False}
        if item.get("id"):
            values["external_id"] = str(item["id"])
        if item.get("permalink"):
            values["external_url"] = item["permalink"]
        if item.get("status"):
            values["external_status"] = item["status"]
        if item.get("price") is not None:
            values["price"] = float(item["price"])
        publication.write(values)
        return result

    def refresh_for_edit(self, publication):
        """Refresh editable publication data before opening a provider wizard."""
        result = self.sync_from_marketplace(publication)
        item = result.get("item") if isinstance(result, dict) else {}
        if not isinstance(item, dict):
            return result
        values = {}
        if isinstance(item.get("attributes"), list):
            values["attributes_json"] = json.dumps(item["attributes"], ensure_ascii=False)
        if isinstance(item.get("pictures"), list):
            values["pictures_json"] = json.dumps(item["pictures"], ensure_ascii=False)
        if item.get("category_id"):
            values["category_ref"] = item["category_id"]
        if item.get("listing_type_id"):
            values["listing_type"] = item["listing_type_id"]
        if values:
            publication.write(values)
        return result

    def import_order(self, account, external_id):
        result = self._get_provider_for_account(account).get_order(external_id)
        order_data = result.get("order") if isinstance(result, dict) else {}
        if not isinstance(order_data, dict):
            raise UserError("El marketplace devolvió una orden inválida.")

        order_ref = "%s:%s" % (account.provider_type or "marketplace", external_id)
        order_model = self.env["sale.order"].sudo()
        existing = order_model.search([("client_order_ref", "=", order_ref)], limit=1)
        previous_state = existing.marketplace_order_state if existing else None
        previous_shipping_status = existing.marketplace_shipping_status if existing else None
        order_values = {
            "marketplace_external_order_id": str(external_id),
            "marketplace_account_id": account.id,
            "marketplace_order_state": self._normalize_order_state(order_data),
            "marketplace_external_status": order_data.get("status") or False,
            "marketplace_sync_date": fields.Datetime.now(),
        }
        if existing:
            existing.write(order_values)
            existing._apply_marketplace_logistics(order_data)
            existing._apply_marketplace_transition()
            existing._emit_marketplace_state_event(previous_state, previous_shipping_status)
            return {
                "order_id": existing.id,
                "external_id": str(external_id),
                "created": False,
                "state": existing.marketplace_order_state,
            }

        buyer = order_data.get("buyer") if isinstance(order_data.get("buyer"), dict) else {}
        buyer_name = buyer.get("nickname") or buyer.get("first_name") or "Marketplace buyer"
        buyer_email = buyer.get("email") or False
        partner_model = self.env["res.partner"].sudo()
        partner = partner_model.search([("ref", "=", order_ref)], limit=1)
        if not partner:
            partner = partner_model.create({"name": buyer_name, "email": buyer_email, "ref": order_ref})

        order = order_model.create(
            {
                "partner_id": partner.id,
                "client_order_ref": order_ref,
                "origin": "Marketplace %s" % external_id,
                **order_values,
            }
        )
        missing_items = []
        for line in order_data.get("order_items") or []:
            item = line.get("item") if isinstance(line, dict) and isinstance(line.get("item"), dict) else {}
            item_id = str(item.get("id") or "")
            variant_id = str(
                line.get("variation_id")
                or line.get("item", {}).get("variation_id")
                or item.get("variation_id")
                or ""
            )
            mapping_domain = [("account_id", "=", account.id), ("external_id", "=", item_id)]
            if variant_id:
                mapping_domain.append(("external_variant_id", "=", variant_id))
            mapping = self.env["marketplace.product.mapping"].sudo().search(mapping_domain, limit=1)
            if mapping and mapping.product_id:
                product = mapping.product_id
            else:
                product = self.env["product.product"].sudo().search(
                    [("default_code", "=", item_id)], limit=1
                )
            if not product and mapping and mapping.sku:
                product = self.env["product.product"].sudo().search(
                    [("default_code", "=", mapping.sku)], limit=1
                )
            if not product:
                missing_items.append(item_id or item.get("title") or "unknown")
                continue
            external_line_id = str(line.get("id") or "") or False
            line_domain = [("order_id", "=", order.id), ("product_id", "=", product.id)]
            if external_line_id:
                line_domain = [
                    ("order_id", "=", order.id),
                    ("marketplace_external_line_id", "=", external_line_id),
                ]
            order_line = order.env["sale.order.line"].sudo().search(line_domain, limit=1)
            line_values = {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": float(line.get("quantity") or 1.0),
                "price_unit": float(line.get("unit_price") or line.get("sale_fee") or 0.0),
                "name": item.get("title") or product.display_name,
                "marketplace_external_line_id": external_line_id,
                "marketplace_external_variant_id": variant_id or False,
            }
            if order_line:
                order_line.write(line_values)
            else:
                order.env["sale.order.line"].sudo().create(line_values)
        order._apply_marketplace_logistics(order_data)
        order._apply_marketplace_transition()
        order._emit_marketplace_state_event()
        return {
            "order_id": order.id,
            "external_id": str(external_id),
            "created": True,
            "state": order.marketplace_order_state,
            "missing_items": missing_items,
        }

    def _normalize_order_state(self, order_data):
        status = str(order_data.get("status") or "").lower()
        shipping = order_data.get("shipping") if isinstance(order_data.get("shipping"), dict) else {}
        shipping_status = str(shipping.get("status") or "").lower()
        if status in {"cancelled", "canceled", "invalid", "refunded", "partially_refunded"}:
            return "cancelled"
        if shipping_status in {"delivered", "delivered_to_buyer"}:
            return "delivered"
        if shipping_status in {"shipped", "in_transit", "ready_to_ship"}:
            return "shipped"
        payments = order_data.get("payments") if isinstance(order_data.get("payments"), list) else []
        if status in {"paid", "confirmed"} or any(
            str(payment.get("status") or "").lower() in {"approved", "paid"}
            for payment in payments
            if isinstance(payment, dict)
        ):
            return "paid"
        return "pending"

    def _get_provider_for_account(self, account):
        if not account:
            raise UserError("La orden necesita una cuenta de marketplace.")
        return self.env["sce.provider.factory"].get_provider(account)

    def delete(self, publication):
        publication.ensure_one()
        if not publication.external_id:
            raise UserError("No se puede eliminar una publicación sin ID externo.")
        result = self._get_provider(publication).delete_product(self._build_payload(publication)) or {}
        publication.write({"state": "draft", "external_id": False, "external_url": False})
        return result