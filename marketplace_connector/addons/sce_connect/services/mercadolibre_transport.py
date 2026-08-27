import logging
from urllib.parse import urlparse

import requests

from .errors import ApiError, AuthenticationError, NetworkError, PermissionError

_logger = logging.getLogger(__name__)


class MercadoLibreConnectTransport:
    API_BASE_URL = "https://api.mercadolibre.com"
    AUTH_BASE_URL = "https://api.mercadolibre.com/oauth/token"
    ALLOWED_HOST = "api.mercadolibre.com"
    ALLOWED_PATHS = frozenset({"/oauth/token", "/users/me"})

    def __init__(self, timeout=30, session=None):
        self.timeout = timeout if timeout and timeout > 0 else 30
        self.session = session or requests.Session()

    def request(self, method, url, *, payload=None, access_token=None, form_encoded=False):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != self.ALLOWED_HOST
            or parsed.path not in self.ALLOWED_PATHS
            or parsed.query
            or parsed.fragment
        ):
            raise ApiError("El endpoint de MercadoLibre no está permitido.")
        headers = {"Accept": "application/json"}
        kwargs = {"method": method, "url": url, "headers": headers, "timeout": self.timeout, "allow_redirects": False}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if form_encoded:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            kwargs["data"] = payload or {}
        else:
            headers["Content-Type"] = "application/json"
            kwargs["json"] = payload or {}
        try:
            response = self.session.request(**kwargs)
        except requests.Timeout as error:
            raise NetworkError("Tiempo de espera agotado al conectar con MercadoLibre.") from error
        except requests.RequestException as error:
            raise NetworkError("No se pudo conectar con MercadoLibre.") from error
        if response.is_redirect or response.is_permanent_redirect:
            raise ApiError("MercadoLibre respondió con una redirección no permitida.")
        if response.status_code == 401:
            raise AuthenticationError("MercadoLibre rechazó la autorización.")
        if response.status_code == 403:
            raise PermissionError("La aplicación no tiene permisos suficientes en MercadoLibre.")
        if response.status_code >= 400:
            raise ApiError(f"MercadoLibre devolvió HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as error:
            raise ApiError("MercadoLibre devolvió una respuesta inválida.") from error
