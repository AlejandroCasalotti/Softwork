# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

HTTP Client

Generic, connector-agnostic HTTP client used by
marketplace API clients (e.g. sce_connector_ml).
"""

from __future__ import annotations

from typing import Any

import requests

from ...exceptions import SCEAPIError, SCEConnectionError
from .auth import AuthStrategy
from .response import HttpResponse


class HttpClient:
    """
    Thin ``requests``-based HTTP client with pluggable authentication.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        *,
        base_url: str,
        auth: AuthStrategy | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        provider: str | None = None,
    ) -> None:

        self.base_url = base_url.rstrip("/") if base_url else ""
        self.auth = auth
        self.timeout = timeout
        self.provider = provider

    # ==========================================================
    # Public API
    # ==========================================================

    def get(self, path, *, params=None, headers=None) -> HttpResponse:
        return self.request("GET", path, params=params, headers=headers)

    def post(self, path, *, json=None, data=None, headers=None) -> HttpResponse:
        return self.request("POST", path, json=json, data=data, headers=headers)

    def put(self, path, *, json=None, data=None, headers=None) -> HttpResponse:
        return self.request("PUT", path, json=json, data=data, headers=headers)

    def patch(self, path, *, json=None, data=None, headers=None) -> HttpResponse:
        return self.request("PATCH", path, json=json, data=data, headers=headers)

    def delete(self, path, *, headers=None) -> HttpResponse:
        return self.request("DELETE", path, headers=headers)

    # ==========================================================
    # Core
    # ==========================================================

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        url = self._build_url(path)
        request_headers = self._build_headers(headers)

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=request_headers,
                timeout=self.timeout,
            )

        except requests.exceptions.Timeout:
            raise SCEConnectionError(
                message="HTTP request timed out",
                provider=self.provider,
                endpoint=url,
            )

        except requests.exceptions.ConnectionError:
            raise SCEConnectionError(
                message="HTTP connection failed",
                provider=self.provider,
                endpoint=url,
            )

        except Exception as error:
            raise SCEConnectionError(
                message=str(error),
                provider=self.provider,
                endpoint=url,
            )

        return self._to_response(response, url)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _build_url(self, path: str) -> str:
        if path.startswith("http"):
            return path

        return f"{self.base_url}/{path.lstrip('/')}"

    def _build_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        result: dict[str, str] = {"Accept": "application/json"}

        if headers:
            result.update(headers)

        if self.auth is not None:
            result = self.auth.apply(result)

        return result

    def _to_response(self, response: requests.Response, url: str) -> HttpResponse:
        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text

            raise SCEAPIError(
                message="HTTP request failed",
                provider=self.provider,
                endpoint=url,
                status_code=response.status_code,
                response=body,
            )

        if not response.content:
            body = {}
        else:
            try:
                body = response.json()
            except ValueError:
                body = response.text

        return HttpResponse(
            status_code=response.status_code,
            body=body,
            headers=dict(response.headers),
        )
