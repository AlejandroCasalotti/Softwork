from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

from .connection_service import ConnectionService
from .log_sanitizer import redact
from .price_policy_calculator import PricePolicyCalculator


class SceConnectPriceService(models.AbstractModel):
    _name = "sce.connect.price.service"
    _description = "SCE Connect Price Synchronization Service"

    SOURCE_FIELD = "list_price"
    PRECISION = Decimal("0.01")

    def _validate_mapping(self, mapping):
        if not mapping or not mapping.exists():
            raise UserError("El mapping de precio no existe.")
        if not mapping.active or mapping.mapping_status != "verified":
            raise UserError("El mapping de precio no está activo y verificado.")
        if not mapping.marketplace_item_id:
            raise UserError(
                "La publicación MercadoLibre no está vinculada. SCE Connect no crea publicaciones."
            )
        mapping._check_identity_scope()
        return mapping

    def _remote_price(self, mapping):
        connection = mapping.external_connection_id
        service = ConnectionService(connection, env=self.env)
        context = service.remote_product_context()
        policy = self._active_policy(mapping)
        if policy:
            if not policy.remote_pricelist_id:
                raise UserError("La política de precio no tiene una lista de precios Odoo configurada.")
            result = service.remote_pricelist_price(
                mapping.external_product_mapping_id.external_id,
                policy.remote_pricelist_id,
                context=context,
            )
            if not isinstance(result, dict) or "price" not in result:
                raise UserError("Odoo remoto no devolvió un precio de lista válido.")
            return result["price"], context
        metadata = service.metadata("product.product")
        if self.SOURCE_FIELD not in metadata:
            raise UserError("El Odoo remoto no expone list_price para sincronizar precio.")
        rows = service.search_read(
            "product.product",
            domain=[("id", "=", mapping.external_product_mapping_id.external_id)],
            fields=["id", self.SOURCE_FIELD],
            limit=1,
            context=context,
        )
        if not rows:
            raise UserError("No se encontró el producto externo para sincronizar precio.")
        return rows[0].get(self.SOURCE_FIELD), context

    def _active_policy(self, mapping):
        if "sce.connect.price.policy" not in self.env:
            return False
        if getattr(mapping.marketplace_account_id, "connect_ownership_state", False) != "ready":
            return False
        return self.env["sce.connect.price.policy"].search(
            [("account_id", "=", mapping.marketplace_account_id.id), ("active", "=", True)],
            limit=1,
        )

    def _apply_policy(self, mapping, base_price, record_error=True):
        policy = self._active_policy(mapping)
        if not policy:
            return {"price": base_price, "blocked": False, "adjustments": "Sin ajustes"}
        result = policy.calculate(base_price, mapping.last_price_sent or None)
        result["adjustments"] = "%.4f%% + %.4f" % (
            policy.adjustment_percent,
            policy.adjustment_fixed,
        )
        if result["blocked"]:
            reason = "Actualización bloqueada por protección de precio de la política."
            if record_error:
                mapping.write({"last_price_error": reason})
            result["message"] = reason
        return result

    @classmethod
    def calculate_price(cls, base_price, _context=None):
        try:
            price = Decimal(str(base_price))
        except (InvalidOperation, TypeError, ValueError):
            raise UserError("El precio remoto no tiene un formato válido.")
        if not price.is_finite() or price <= 0:
            raise UserError("El precio remoto debe ser mayor que cero.")
        return price.quantize(cls.PRECISION, rounding=ROUND_HALF_UP)

    def _provider_payload(self, mapping, price):
        payload = {"item_id": mapping.marketplace_item_id, "price": float(price)}
        if mapping.marketplace_variation_id:
            payload["variation_id"] = mapping.marketplace_variation_id
        return payload

    def _apply_rules(self, mapping, price):
        context = {
            "price": price,
            "cost": mapping.external_product_mapping_id.standard_price,
            "sku": mapping.external_product_mapping_id.default_code or False,
            "barcode": mapping.external_product_mapping_id.barcode or False,
            "active": mapping.external_product_mapping_id.active,
        }
        result = self.env["sce.connect.rule.engine"].evaluate(mapping.tenant_id, "price", context)
        if not result.get("allowed", True):
            reason = "Sincronización de precio bloqueada por regla %s." % result.get("blocked_by")
            mapping.write({"last_price_error": reason})
            return result, None
        final_price = self.calculate_price(result.get("value", price), context)
        return result, final_price

    def _write_mappings(self, mappings, values):
        if hasattr(mappings, "write") and hasattr(mappings, "__iter__"):
            mappings.write(values)
            return
        for mapping in self._iter_mappings(mappings):
            mapping.write(values)

    @staticmethod
    def _iter_mappings(mappings):
        if isinstance(mappings, (list, tuple, set)):
            return mappings
        if hasattr(mappings, "__iter__"):
            return mappings
        return mappings if isinstance(mappings, (list, tuple, set)) else [mappings]

    def _prepare_sync_price(self, mapping):
        source_price, _context = self._remote_price(mapping)
        source_price = self.calculate_price(source_price, {"marketplace_mapping_id": mapping.id})
        policy_result = self._apply_policy(mapping, source_price)
        if policy_result["blocked"]:
            return {"blocked": True, "reason": policy_result["message"]}
        rule_result, final_price = self._apply_rules(mapping, policy_result["price"])
        if not rule_result.get("allowed", True):
            return {"blocked": True, "blocked_by": rule_result.get("blocked_by")}
        return {
            "blocked": False,
            "source_price": source_price,
            "source_text": format(source_price, "f"),
            "sent_price": final_price,
            "sent_text": format(final_price, "f"),
        }

    def _read_item(self, mapping):
        provider = ProviderFactory.get_provider(mapping.marketplace_account_id)
        result = provider.get_item(mapping.marketplace_item_id, params={"include_attributes": "all"}) or {}
        item = result.get("item") if isinstance(result, dict) else None
        if not isinstance(item, dict):
            raise UserError("No se pudo leer la publicación MercadoLibre existente.")
        unsupported_keys = {
            "user_product_id",
            "family_id",
            "user_product_listing",
            "warehouse_management",
            "selling_address",
        }
        if any(item.get(key) for key in unsupported_keys):
            raise UserError("La publicación utiliza un modelo User Products/Multi-Origin no soportado por C.2.")
        automation = item.get("price_automation") or item.get("automatic_pricing") or item.get("price_automation_active")
        if automation:
            raise UserError("PRICE_AUTOMATION_ACTIVE: la publicación no permite actualizar precio mediante API.")
        return provider, item

    def _item_mappings(self, mapping):
        return self.env["sce.connect.marketplace.mapping"].search(
            [
                ("marketplace_account_id", "=", mapping.marketplace_account_id.id),
                ("marketplace_item_id", "=", mapping.marketplace_item_id),
                ("external_connection_id", "=", mapping.external_connection_id.id),
                ("active", "=", True),
                ("mapping_status", "=", "verified"),
            ]
        )

    def sync_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        try:
            provider, item = self._read_item(mapping)
            item_mappings = self._item_mappings(mapping) if item.get("variations") else mapping
            if item.get("variations"):
                ml_variation_ids = [
                    str(variation.get("id"))
                    for variation in item["variations"]
                    if isinstance(variation, dict) and variation.get("id") is not None
                ]
                if len(ml_variation_ids) != len(set(ml_variation_ids)):
                    raise UserError("La publicación MercadoLibre contiene variation_id duplicados.")
                ml_variation_ids = set(ml_variation_ids)
                mapping_variation_ids = [
                    str(item_mapping.marketplace_variation_id)
                    for item_mapping in item_mappings
                    if item_mapping.marketplace_variation_id
                ]
                if len(mapping_variation_ids) != len(set(mapping_variation_ids)):
                    raise UserError("Los mappings SCE Connect contienen variation_id duplicados.")
                mapping_variation_ids = set(mapping_variation_ids)
                if ml_variation_ids != mapping_variation_ids:
                    raise UserError(
                        "Existe una discrepancia entre las variaciones de MercadoLibre y los mappings de SCE Connect."
                    )
                prepared_prices = []
                for item_mapping in item_mappings:
                    prepared = self._prepare_sync_price(item_mapping)
                    if prepared["blocked"]:
                        return {"ok": True, "blocked": True, **{k: v for k, v in prepared.items() if k != "blocked"}}
                    prepared_prices.append(prepared)
                if not prepared_prices:
                    raise UserError("La publicación tiene variaciones pero no hay mappings verificados.")
                if len({item["source_text"] for item in prepared_prices}) != 1:
                    raise UserError("Las variantes de esta publicación requieren un precio común, pero Odoo tiene precios diferentes.")
                if len({item["sent_text"] for item in prepared_prices}) != 1:
                    raise UserError(
                        "Las variantes de esta publicación requieren un precio común, pero la configuración actual produce precios diferentes."
                    )
                price = prepared_prices[0]["sent_price"]
                source_text = prepared_prices[0]["source_text"]
                sent_text = prepared_prices[0]["sent_text"]
                variation_prices = [
                    {"id": item_mapping.marketplace_variation_id, "price": float(price)}
                    for item_mapping in item_mappings
                    if item_mapping.marketplace_variation_id
                ]
                if len(variation_prices) != len(item_mappings):
                    raise UserError("Falta variation_id en una variante de la publicación.")
                payload = {"item_id": mapping.marketplace_item_id, "variation_prices": variation_prices}
                state_targets = item_mappings
            else:
                prepared = self._prepare_sync_price(mapping)
                if prepared["blocked"]:
                    return {"ok": True, "blocked": True, **{k: v for k, v in prepared.items() if k != "blocked"}}
                price = prepared["sent_price"]
                source_text = prepared["source_text"]
                sent_text = prepared["sent_text"]
                payload = self._provider_payload(mapping, price)
                state_targets = mapping
            if all(
                target.last_price_sync_at
                and target.last_price_source == source_text
                and target.last_price_sent == sent_text
                for target in self._iter_mappings(state_targets)
            ):
                return {"ok": True, "skipped": True, "source_price": source_text, "price": sent_text}
            result = provider.update_price(payload) or {}
            self._write_mappings(
                state_targets,
                {
                    "last_price_source": source_text,
                    "last_price_sent": sent_text,
                    "last_price_sync_at": fields.Datetime.now(),
                    "last_price_error": False,
                },
            )
            result = dict(result)
            result.setdefault("source_price", source_text)
            result.setdefault("price", sent_text)
            return result
        except Exception as error:
            mapping.write({"last_price_error": redact(str(error))})
            raise

    def preview_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        source_price, _context = self._remote_price(mapping)
        base_price = self.calculate_price(source_price, {"marketplace_mapping_id": mapping.id})
        result = self._apply_policy(mapping, base_price, record_error=False)
        return {
            "base_price": format(base_price, "f"),
            "adjustments": result.get("adjustments", "Sin ajustes"),
            "price": format(result["price"], "f") if not result["blocked"] else False,
            "blocked": result["blocked"],
            "message": result.get("message"),
        }

    def enqueue_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        jobs = self.env["sce.job"]
        pending = jobs.search(
            [
                ("job_type", "=", "sync_connect_price"),
                ("connect_marketplace_mapping_id", "=", mapping.id),
                ("state", "in", ["queued", "running"]),
            ],
            limit=1,
        )
        if pending:
            return pending
        return jobs.create(
            {
                "name": "Sync Connect Price - %s" % mapping.marketplace_item_id,
                "account_id": mapping.marketplace_account_id.id,
                "job_type": "sync_connect_price",
                "connect_marketplace_mapping_id": mapping.id,
                "payload_json": "{}",
            }
        )