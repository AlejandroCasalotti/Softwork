import ipaddress
import socket
from urllib.parse import urlparse

import requests

from .errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DatabaseError,
    NetworkError,
    OperationBlocked,
    PermissionError,
)
from .odoo_adapter import BaseOdooAdapter


class Odoo19Json2Adapter(BaseOdooAdapter):
    DEFAULT_TIMEOUT = 30
    DEFAULT_MODELS = (
        "res.partner",
        "product.template",
        "product.product",
        "stock.warehouse",
    )
    ALLOWED_EXECUTE_METHODS = frozenset()

    def __init__(
        self,
        *,
        base_url,
        database,
        user,
        secret_storage,
        secret_ref,
        timeout=DEFAULT_TIMEOUT,
        allow_insecure_http=False,
        allow_private_network=False,
        session=None,
    ):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.database = (database or "").strip()
        self.user = (user or "").strip()
        self.secret_storage = secret_storage
        self.secret_ref = secret_ref
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.allow_insecure_http = bool(allow_insecure_http)
        self.allow_private_network = bool(allow_private_network)
        self.session = session or requests.Session()
        self._validate_target()

    def _validate_target(self):
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            raise ConfigurationError("La URL de Odoo debe ser válida y no incluir credenciales.")
        if parsed.scheme != "https" and not self.allow_insecure_http:
            raise ConfigurationError("La conexión a Odoo requiere HTTPS.")
        if self.timeout <= 0:
            raise ConfigurationError("El timeout debe ser mayor que cero.")
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
            if not self.allow_private_network:
                raise ConfigurationError("El destino local está bloqueado por protección SSRF.")
            return
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(hostname, parsed.port, type=socket.SOCK_STREAM)
            }
        except OSError as error:
            raise NetworkError("No se pudo resolver el host de Odoo.") from error
        if not self.allow_private_network and any(self._is_private_address(address) for address in addresses):
            raise ConfigurationError("El destino pertenece a una red privada bloqueada por protección SSRF.")

    @staticmethod
    def _is_private_address(address):
        parsed = ipaddress.ip_address(address)
        return (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_reserved
            or parsed.is_unspecified
        )

    def _secret(self):
        if not self.secret_ref:
            raise ConfigurationError("Falta la referencia al secreto de Odoo.")
        return self.secret_storage.decrypt(self.secret_ref)

    def _call(self, model, method, params):
        if not model or not method:
            raise ConfigurationError("Modelo y método son obligatorios.")
        url = f"{self.base_url}/json/2/{model}/{method}"
        headers = {
            "Authorization": f"Bearer {self._secret()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = self.session.post(
                url,
                json=params or {},
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.Timeout as error:
            raise NetworkError("Se agotó el tiempo de espera al conectar con Odoo.") from error
        except requests.RequestException as error:
            raise NetworkError("No se pudo conectar con Odoo.") from error
        if response.is_redirect or response.is_permanent_redirect:
            raise ApiError("Odoo respondió con una redirección no permitida.")
        if response.status_code == 401:
            raise AuthenticationError("Odoo rechazó la autenticación del usuario técnico.")
        if response.status_code == 403:
            raise PermissionError("El usuario técnico no tiene permisos suficientes en Odoo.")
        if response.status_code == 404:
            raise DatabaseError("No se encontró el endpoint JSON-2 o la base de datos de Odoo.")
        if response.status_code >= 400:
            raise ApiError(f"Odoo devolvió un error HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as error:
            raise ApiError("Odoo devolvió una respuesta JSON inválida.") from error

    def test_connection(self):
        checks = {}
        for model in self.DEFAULT_MODELS:
            checks[model] = self.search_read(model, fields=["id"], limit=1)
        return {"status": "connected", "database": self.database, "models": checks}

    def read(self, model, ids, fields=None):
        return self._call(model, "read", {"ids": ids, "fields": fields or []})

    def search(self, model, domain=None, offset=0, limit=None, order=None):
        params = {"domain": domain or [], "offset": offset}
        if limit is not None:
            params["limit"] = limit
        if order:
            params["order"] = order
        return self._call(model, "search", params)

    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None):
        params = {"domain": domain or [], "fields": fields or [], "offset": offset}
        if limit is not None:
            params["limit"] = limit
        if order:
            params["order"] = order
        return self._call(model, "search_read", params)

    def create(self, model, values):
        return self._call(model, "create", {"vals_list": values if isinstance(values, list) else [values]})

    def write(self, model, ids, values):
        return self._call(model, "write", {"ids": ids, "vals": values})

    def unlink(self, model, ids):
        if model not in self.ALLOWED_EXECUTE_METHODS:
            raise OperationBlocked("unlink está bloqueado por defecto en Fase 1.")
        return self._call(model, "unlink", {"ids": ids})

    def execute(self, model, method, args=None, kwargs=None):
        if (model, method) not in self.ALLOWED_EXECUTE_METHODS:
            raise OperationBlocked("execute está bloqueado por defecto en Fase 1.")
        return self._call(model, method, {"args": args or [], "kwargs": kwargs or {}})

    def metadata(self, model):
        return self._call(model, "fields_get", {"attributes": ["string", "type", "relation", "required", "readonly"]})
