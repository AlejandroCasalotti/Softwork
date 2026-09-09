import logging

from odoo import fields, models
from odoo.exceptions import UserError

from ..services.connection_service import ConnectionService
from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

from .log_sanitizer import redact


_logger = logging.getLogger(__name__)


class SceConnectStockService(models.AbstractModel):
    _name = "sce.connect.stock.service"
    _description = "SCE Connect Stock Synchronization Service"

    SOURCE_FIELD = "free_qty"
    RETRYABLE_PROVIDER_ERRORS = ("429", "500", "502", "503", "504", "timeout")

    def _validate_mapping(self, mapping):
        if not mapping or not mapping.exists():
            raise UserError("El mapping de stock no existe.")
        if not mapping.active or mapping.mapping_status != "verified":
            raise UserError("El mapping de stock no está activo y verificado.")
        if not mapping.marketplace_item_id:
            raise UserError(
                "La publicación MercadoLibre no está vinculada. SCE Connect no crea publicaciones."
            )
        mapping._check_identity_scope()
        if mapping.marketplace_variation_id and not mapping.external_product_mapping_id:
            raise UserError("La variación MercadoLibre no tiene producto externo asociado.")
        return mapping

    def _remote_stock(self, mapping):
        connection = mapping.external_connection_id
        context = ConnectionService(connection, env=self.env).remote_product_context()
        product_service = ConnectionService(connection, env=self.env)
        metadata = product_service.metadata("product.product")
        if self.SOURCE_FIELD not in metadata:
            raise UserError("El Odoo remoto no expone free_qty para sincronizar stock.")
        rows = product_service.search_read(
            "product.product",
            domain=[("id", "=", mapping.external_product_mapping_id.external_id)],
            fields=["id", self.SOURCE_FIELD],
            limit=1,
            context=context,
        )
        if not rows:
            raise UserError("No se encontró el producto externo para sincronizar stock.")
        source_value = rows[0].get(self.SOURCE_FIELD)
        try:
            source_stock = int(float(source_value or 0))
        except (TypeError, ValueError):
            raise UserError("El stock remoto no tiene un valor numérico válido.")
        return max(0, source_stock), context

    def _provider_payload(self, mapping, quantity):
        payload = {
            "item_id": mapping.marketplace_item_id,
            "available_quantity": quantity,
        }
        if mapping.marketplace_variation_id:
            payload["variation_id"] = mapping.marketplace_variation_id
        return payload

    def _apply_rules(self, mapping, source_stock):
        context = {
            "stock": source_stock,
            "sku": mapping.external_product_mapping_id.default_code or False,
            "barcode": mapping.external_product_mapping_id.barcode or False,
            "active": mapping.external_product_mapping_id.active,
        }
        result = self.env["sce.connect.rule.engine"].evaluate(mapping.tenant_id, "stock", context)
        if not result.get("allowed", True):
            reason = "Sincronización de stock bloqueada por regla %s." % result.get("blocked_by")
            mapping.write({"last_stock_error": reason})
            return result, None
        try:
            final_stock = max(0, int(float(result.get("value", source_stock))))
        except (TypeError, ValueError):
            raise UserError("La regla de stock produjo un valor inválido.")
        return result, final_stock

    def sync_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        try:
            source_stock, _context = self._remote_stock(mapping)
            rule_result, final_stock = self._apply_rules(mapping, source_stock)
            if not rule_result.get("allowed", True):
                return {
                    "ok": True,
                    "blocked": True,
                    "blocked_by": rule_result.get("blocked_by"),
                    "source_stock": source_stock,
                }
            if (
                mapping.last_stock_sync_at
                and mapping.last_stock_source == source_stock
                and mapping.last_stock_sent == final_stock
            ):
                return {
                    "ok": True,
                    "skipped": True,
                    "source_stock": source_stock,
                    "available_quantity": final_stock,
                }
            provider = ProviderFactory.get_provider(mapping.marketplace_account_id)
            result = provider.update_stock(self._provider_payload(mapping, final_stock)) or {}
            mapping.write(
                {
                    "last_stock_source": source_stock,
                    "last_stock_sent": final_stock,
                    "last_stock_sync_at": fields.Datetime.now(),
                    "last_stock_error": False,
                }
            )
            result = dict(result)
            result.setdefault("source_stock", source_stock)
            result.setdefault("available_quantity", final_stock)
            return result
        except Exception as error:
            safe_error = redact(str(error))
            mapping.write({"last_stock_error": safe_error})
            _logger.error(
                "Stock Connect falló tenant=%s connection=%s external_mapping=%s item=%s variation=%s error=%s",
                mapping.tenant_id.id,
                mapping.external_connection_id.id,
                mapping.external_product_mapping_id.id,
                mapping.marketplace_item_id,
                mapping.marketplace_variation_id or False,
                safe_error,
            )
            raise

    def enqueue_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        job_model = self.env["sce.job"]
        pending = job_model.search(
            [
                ("job_type", "=", "sync_connect_stock"),
                ("connect_marketplace_mapping_id", "=", mapping.id),
                ("state", "in", ["queued", "running"]),
            ],
            limit=1,
        )
        if pending:
            return pending
        return job_model.create(
            {
                "name": "Sync Connect Stock - %s" % mapping.marketplace_item_id,
                "account_id": mapping.marketplace_account_id.id,
                "job_type": "sync_connect_stock",
                "connect_marketplace_mapping_id": mapping.id,
                "payload_json": "{}",
            }
        )