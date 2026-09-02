import logging
from datetime import datetime, timezone

from .errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DatabaseError,
    NetworkError,
    PermissionError,
    SecretStorageError,
)
from .odoo19_json2_adapter import Odoo19Json2Adapter
from .log_sanitizer import redact
from .secret_storage import SecretStorage


_logger = logging.getLogger(__name__)


class ConnectionService:
    STATUS_MAP = {
        AuthenticationError: "authentication_error",
        PermissionError: "permission_error",
        DatabaseError: "database_error",
        NetworkError: "network_error",
        ApiError: "api_error",
        ConfigurationError: "invalid_configuration",
        SecretStorageError: "invalid_configuration",
    }

    def __init__(self, connection, env=None, session=None):
        self.connection = connection
        self.env = env
        self.session = session

    def _adapter(self):
        secret = self.connection.secret_id.with_context(sce_backend_secret_access=True).get_value()
        storage = SecretStorage.from_environment()
        return Odoo19Json2Adapter(
            base_url=self.connection.url,
            database=self.connection.database,
            user=self.connection.user,
            secret_storage=storage,
            secret_ref=storage.encrypt(secret),
            timeout=self.connection.timeout_seconds,
            allow_insecure_http=self.connection.allow_insecure_http,
            allow_private_network=self.connection.allow_private_network,
            session=self.session,
        )

    def test_connection(self):
        try:
            result = self._adapter().test_connection()
        except Exception as error:
            status = next(
                (value for error_type, value in self.STATUS_MAP.items() if isinstance(error, error_type)),
                "api_error",
            )
            self._record_result(status, str(error))
            self._log("SCE Connect connection test failed", status, str(error), "ERROR")
            return {"status": status, "message": str(error)}
        self._record_result("connected", False)
        self._log("SCE Connect connection test succeeded", "connected", False, "INFO")
        return result | {"status": "connected"}

    def metadata(self, model):
        return self._adapter().metadata(model)

    def read(self, model, ids, fields=None):
        return self._adapter().read(model, ids, fields)

    def search(self, model, domain=None, offset=0, limit=None, order=None):
        return self._adapter().search(
            model, domain=domain, offset=offset, limit=limit, order=order
        )

    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None):
        return self._adapter().search_read(
            model, domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

    def test_controlled_write(self):
        adapter = self._adapter()
        marker = f"[SCE CONNECT TEST] {datetime.now(timezone.utc).isoformat()}"
        created = adapter.create("res.partner", {"name": marker, "active": False})
        ids = created if isinstance(created, list) else [created]
        if ids and isinstance(ids[0], dict):
            ids = [item["id"] for item in ids]
        adapter.write("res.partner", ids, {"comment": "SCE Connect controlled write test"})
        return {"status": "completed", "record_ids": ids, "reversible": True}

    def _record_result(self, status, message):
        values = {
            "last_test_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "last_test_status": status,
            "last_error": message or False,
        }
        self.connection.sudo().write(values)

    def _log(self, name, status, message, level):
        log_method = getattr(_logger, level.lower(), _logger.info)
        log_method(
            "%s tenant_id=%s status=%s message=%s",
            name,
            self.connection.tenant_id.id,
            status,
            redact(message or status),
        )
