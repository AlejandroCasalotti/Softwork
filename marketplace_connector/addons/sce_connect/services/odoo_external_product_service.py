import logging
from datetime import datetime, timezone

from .connection_service import ConnectionService
from .errors import ApiError, AuthenticationError, ConfigurationError, NetworkError, PermissionError
from .log_sanitizer import redact

_logger = logging.getLogger(__name__)


class OdooExternalProductService:
    """Read-only product synchronization from an external Odoo (JSON-2) connection.

    Reuses ConnectionService/Odoo19Json2Adapter exclusively; never opens its own
    HTTP client, adapter or authentication.
    """

    DEFAULT_BATCH_SIZE = 100
    NETWORK_RETRY_ATTEMPTS = 2

    NON_RETRYABLE_ERRORS = (AuthenticationError, PermissionError, ConfigurationError)
    RETRYABLE_ERRORS = (NetworkError, ApiError)

    TEMPLATE_MODEL = "product.template"
    VARIANT_MODEL = "product.product"

    TEMPLATE_FIELDS = (
        "id",
        "name",
        "default_code",
        "barcode",
        "list_price",
        "standard_price",
        "active",
        "write_date",
        "categ_id",
        "description_sale",
        "product_variant_ids",
    )
    VARIANT_FIELDS = (
        "id",
        "product_tmpl_id",
        "name",
        "default_code",
        "barcode",
        "active",
        "write_date",
        "product_template_attribute_value_ids",
    )

    def __init__(self, connection, env=None, session=None, batch_size=None):
        connection.ensure_one()
        self.connection = connection
        self.env = env or connection.env
        self.connection_service = ConnectionService(connection, env=self.env, session=session)
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE

    # -- Metadata -----------------------------------------------------

    def _available_fields(self, model, requested_fields):
        metadata = self._call_with_retry(self.connection_service.metadata, model)
        available = [name for name in requested_fields if name in metadata]
        missing = [name for name in requested_fields if name not in metadata]
        if missing:
            _logger.warning(
                "Campos no disponibles en %s (connection=%s): %s",
                model,
                self.connection.id,
                missing,
            )
        return available, missing

    # -- Reads (paginated) ---------------------------------------------

    def _call_with_retry(self, func, *args, **kwargs):
        attempts = 0
        while True:
            try:
                return func(*args, **kwargs)
            except self.RETRYABLE_ERRORS:
                attempts += 1
                if attempts > self.NETWORK_RETRY_ATTEMPTS:
                    raise

    def _fetch_or_raise(self, label, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except self.NON_RETRYABLE_ERRORS as error:
            _logger.error(
                "Sync de %s detenido (no reintentable) tenant=%s connection=%s error=%s",
                label, self.connection.tenant_id.id, self.connection.id, redact(str(error)),
            )
            raise
        except self.RETRYABLE_ERRORS as error:
            _logger.error(
                "Sync de %s detenido (reintentos agotados) tenant=%s connection=%s error=%s",
                label, self.connection.tenant_id.id, self.connection.id, redact(str(error)),
            )
            raise

    def iter_records(self, model, fields, domain=None):
        # offset/limit: deletes concurrentes en el externo durante el run pueden saltear registros (riesgo documentado, no resuelto).
        offset = 0
        while True:
            batch = self._call_with_retry(
                self.connection_service.search_read,
                model,
                domain=domain or [],
                fields=list(fields),
                offset=offset,
                limit=self.batch_size,
                order="id asc",
            )
            if not batch:
                return
            for record in batch:
                yield record
            if len(batch) < self.batch_size:
                return
            offset += self.batch_size

    def list_templates(self, domain=None):
        available, missing = self._available_fields(self.TEMPLATE_MODEL, self.TEMPLATE_FIELDS)
        records = list(self.iter_records(self.TEMPLATE_MODEL, available, domain=domain))
        return records, missing

    def list_variants(self, domain=None):
        available, missing = self._available_fields(self.VARIANT_MODEL, self.VARIANT_FIELDS)
        records = list(self.iter_records(self.VARIANT_MODEL, available, domain=domain))
        return records, missing

    # -- Mapping / idempotent upsert -------------------------------------

    def _upsert_mapping(self, model, record, missing_fields, parent_mapping=None):
        Mapping = self.env["sce.external.product.mapping"].sudo()
        existing = Mapping.search(
            [
                ("external_connection_id", "=", self.connection.id),
                ("external_model", "=", model),
                ("external_id", "=", record["id"]),
            ],
            limit=1,
        )
        values = {
            "external_connection_id": self.connection.id,
            "external_model": model,
            "external_id": record["id"],
            "external_write_date": record.get("write_date") or False,
            "name": record.get("name") or False,
            "default_code": record.get("default_code") or False,
            "barcode": record.get("barcode") or False,
            "list_price": record.get("list_price") or 0.0,
            "standard_price": record.get("standard_price") or 0.0,
            "active": record.get("active", True),
            "missing_fields_json": ",".join(missing_fields) if missing_fields else False,
            "last_synced_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        if parent_mapping is not None:
            values["parent_mapping_id"] = parent_mapping.id
        if existing:
            existing.write(values)
            return existing, "updated"
        return Mapping.create(values), "created"

    def _resolve_parent_mapping(self, tmpl_external_id, template_mappings_by_external_id):
        parent_mapping = template_mappings_by_external_id.get(tmpl_external_id)
        if parent_mapping is not None:
            return parent_mapping
        if tmpl_external_id is None:
            return None
        Mapping = self.env["sce.external.product.mapping"].sudo()
        return Mapping.search(
            [
                ("external_connection_id", "=", self.connection.id),
                ("external_model", "=", self.TEMPLATE_MODEL),
                ("external_id", "=", tmpl_external_id),
            ],
            limit=1,
        ) or None

    # -- Orchestrator ------------------------------------------------

    def sync_products(self, full=False):
        self.connection.ensure_one()
        started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        summary = {
            "records_read": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "errors": [],
        }
        domain = []
        if not full and self.connection.last_product_sync:
            domain = [("write_date", ">", fields_datetime_to_str(self.connection.last_product_sync))]

        # Fetch completo antes de persistir: una falla repite el trabajo de páginas ya leídas de este run (limitación aceptada).
        templates, missing_tmpl_fields = self._fetch_or_raise("productos", self.list_templates, domain=domain)

        template_mappings_by_external_id = {}
        for record in templates:
            summary["records_read"] += 1
            mapping, action = self._upsert_mapping(self.TEMPLATE_MODEL, record, missing_tmpl_fields)
            template_mappings_by_external_id[record["id"]] = mapping
            summary["records_created" if action == "created" else "records_updated"] += 1

        # Las variantes se leen siempre, incluso si su template no cambió en este run (ver _resolve_parent_mapping).
        variants, missing_variant_fields = self._fetch_or_raise("variantes", self.list_variants, domain=domain)
        for record in variants:
            tmpl_ref = record.get("product_tmpl_id")
            tmpl_external_id = tmpl_ref[0] if isinstance(tmpl_ref, (list, tuple)) else tmpl_ref
            parent_mapping = self._resolve_parent_mapping(tmpl_external_id, template_mappings_by_external_id)
            if parent_mapping is None:
                summary["records_skipped"] += 1
                _logger.warning(
                    "Variante externa %s omitida: no existe mapping de template %s (connection=%s).",
                    record.get("id"), tmpl_external_id, self.connection.id,
                )
                continue
            summary["records_read"] += 1
            _mapping, action = self._upsert_mapping(
                self.VARIANT_MODEL, record, missing_variant_fields, parent_mapping=parent_mapping
            )
            summary["records_created" if action == "created" else "records_updated"] += 1

        duration_ms = int((datetime.now(timezone.utc).replace(tzinfo=None) - started_at).total_seconds() * 1000)
        summary["duration_ms"] = duration_ms
        self.connection.sudo().write({"last_product_sync": started_at})

        _logger.info(
            "Sync de productos completado tenant=%s connection=%s batch_size=%s "
            "records_read=%s created=%s updated=%s skipped=%s duration_ms=%s",
            self.connection.tenant_id.id,
            self.connection.id,
            self.batch_size,
            summary["records_read"],
            summary["records_created"],
            summary["records_updated"],
            summary["records_skipped"],
            duration_ms,
        )
        return summary


def fields_datetime_to_str(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value
