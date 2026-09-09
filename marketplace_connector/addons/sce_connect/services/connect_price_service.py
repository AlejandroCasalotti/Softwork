from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

from .connection_service import ConnectionService
from .log_sanitizer import redact


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

    def sync_mapping(self, mapping):
        mapping = self._validate_mapping(mapping)
        try:
            source_price, _context = self._remote_price(mapping)
            price = self.calculate_price(source_price, {"marketplace_mapping_id": mapping.id})
            source_text = format(price, "f")
            if (
                mapping.last_price_sync_at
                and mapping.last_price_source == source_text
                and mapping.last_price_sent == source_text
            ):
                return {"ok": True, "skipped": True, "source_price": source_text, "price": source_text}
            provider = ProviderFactory.get_provider(mapping.marketplace_account_id)
            result = provider.update_price(self._provider_payload(mapping, price)) or {}
            mapping.write(
                {
                    "last_price_source": source_text,
                    "last_price_sent": source_text,
                    "last_price_sync_at": fields.Datetime.now(),
                    "last_price_error": False,
                }
            )
            result = dict(result)
            result.setdefault("source_price", source_text)
            result.setdefault("price", source_text)
            return result
        except Exception as error:
            mapping.write({"last_price_error": redact(str(error))})
            raise

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