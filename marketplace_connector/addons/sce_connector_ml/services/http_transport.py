# -*- coding: utf-8 -*-
import logging
import time

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class MercadoLibreHttpTransport:
    """HTTP transport owned by the MercadoLibre connector."""

    def _ensure_requests(self):
        if not requests:
            raise UserError("La librería Python 'requests' no está disponible en el entorno Odoo.")

    def _request(self, method, endpoint, payload=None, params=None, with_auth=True, form_encoded=False, _retried=False):
        self._ensure_requests()
        headers = {"Content-Type": "application/json"}
        if form_encoded:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if with_auth:
            token = self.account.access_token
            if not token:
                raise UserError("No hay access token configurado en la cuenta.")
            headers["Authorization"] = f"Bearer {token}"

        url = endpoint if endpoint.startswith("http") else f"{self.BASE_API_URL}{endpoint}"
        timeout = int(self.account.provider_timeout_seconds or 30)
        if timeout <= 0:
            timeout = 30
        started = time.monotonic()
        try:
            kwargs = {
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
            if form_encoded:
                kwargs["data"] = payload
            else:
                kwargs["json"] = payload
            response = requests.request(**kwargs)
        except requests.Timeout:
            raise UserError(f"Tiempo de espera agotado ({timeout}s) al conectar con MercadoLibre.")
        except requests.RequestException as error:
            raise UserError(f"Error de red con MercadoLibre: {error}")

        elapsed_ms = int((time.monotonic() - started) * 1000)
        if response.status_code in (401, 403) and with_auth and not _retried and self.account.refresh_token:
            refresh_result = self.refresh_token()
            if self._persist_refreshed_tokens(refresh_result):
                return self._request(
                    method,
                    endpoint,
                    payload=payload,
                    params=params,
                    with_auth=with_auth,
                    form_encoded=form_encoded,
                    _retried=True,
                )
        if response.status_code >= 400:
            payload_keys = sorted(payload) if isinstance(payload, dict) else []
            _logger.error(
                "ML error HTTP %s en %s %s account_id=%s payload_keys=%s response=%s",
                response.status_code,
                method,
                endpoint,
                self.account.id,
                payload_keys,
                response.text,
            )
            raise UserError(
                f"Error MercadoLibre {response.status_code} en {method} {endpoint} "
                f"(campos enviados: {', '.join(payload_keys) or 'ninguno'}): {response.text}"
            )
        if not response.text:
            return {"_meta": {"elapsed_ms": elapsed_ms}}
        data = response.json()
        if isinstance(data, dict):
            data.setdefault("_meta", {})["elapsed_ms"] = elapsed_ms
        return data
