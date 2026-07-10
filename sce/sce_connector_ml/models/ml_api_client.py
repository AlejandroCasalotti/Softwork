# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre API Client
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests

from odoo import models

_logger = logging.getLogger(__name__)


class MLAPIClient(models.AbstractModel):
    """
    Generic Mercado Libre HTTP client.
    """

    _name = "ml.api.client"
    _description = "Mercado Libre API Client"

    BASE_URL = "https://api.mercadolibre.com"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _settings(self):
        ICP = self.env["ir.config_parameter"].sudo()

        return {
            "timeout": int(
                ICP.get_param(
                    "sce.http_timeout",
                    60,
                )
            ),
            "retries": int(
                ICP.get_param(
                    "sce.http_retries",
                    3,
                )
            ),
        }

    # -------------------------------------------------------------------------

    def _url(
        self,
        endpoint,
    ):
        """
        Builds complete URL.
        """

        return urljoin(
            self.BASE_URL,
            endpoint.lstrip("/"),
        )

    # -------------------------------------------------------------------------

    def _headers(
        self,
        account,
        headers=None,
    ):
        """
        Builds HTTP headers.
        """

        result = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if account.access_token:

            result[
                "Authorization"
            ] = (
                "Bearer %s"
                % account.access_token
            )

        if headers:

            result.update(headers)

        return result

    # -------------------------------------------------------------------------

    def _request(
        self,
        account,
        method,
        endpoint,
        *,
        params=None,
        json=None,
        data=None,
        files=None,
        headers=None,
    ):
        """
        Generic HTTP request.
        """

        settings = self._settings()

        url = self._url(
            endpoint,
        )

        request_headers = self._headers(
            account,
            headers,
        )

        if files:

            request_headers.pop(
                "Content-Type",
                None,
            )

        response = requests.request(

            method=method,

            url=url,

            params=params,

            json=json,

            data=data,

            files=files,

            headers=request_headers,

            timeout=settings["timeout"],

        )

        if response.status_code == 401:

            self.env[
                "ml.auth.service"
            ].refresh_token(
                account
            )

            request_headers = self._headers(
                account,
                headers,
            )

            response = requests.request(

                method=method,

                url=url,

                params=params,

                json=json,

                data=data,

                files=files,

                headers=request_headers,

                timeout=settings["timeout"],

            )

        self._log_response(
            account,
            method,
            endpoint,
            response,
        )

        response.raise_for_status()

        if not response.content:

            return {}

        if "application/json" in response.headers.get(
            "Content-Type",
            "",
        ):

            return response.json()

        return response.text

    # -------------------------------------------------------------------------

    def _log_response(
        self,
        account,
        method,
        endpoint,
        response,
    ):
        """
        Stores request log.
        """

        try:

            self.env[
                "sce.log"
            ].log_info(

                "%s %s"

                % (
                    method,
                    endpoint,
                ),

                account_id=account.id,

                category="connection",

                response={

                    "status": response.status_code,

                },

            )

        except Exception:

            _logger.exception(
                "Unable to create SCE log."
            )

                # -------------------------------------------------------------------------
    # GET
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        endpoint,
        params=None,
        headers=None,
    ):
        """
        Executes GET request.
        """

        return self._request(
            account,
            "GET",
            endpoint,
            params=params,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # POST
    # -------------------------------------------------------------------------

    def post(
        self,
        account,
        endpoint,
        json=None,
        data=None,
        headers=None,
    ):
        """
        Executes POST request.
        """

        return self._request(
            account,
            "POST",
            endpoint,
            json=json,
            data=data,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # PUT
    # -------------------------------------------------------------------------

    def put(
        self,
        account,
        endpoint,
        json=None,
        data=None,
        headers=None,
    ):
        """
        Executes PUT request.
        """

        return self._request(
            account,
            "PUT",
            endpoint,
            json=json,
            data=data,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # PATCH
    # -------------------------------------------------------------------------

    def patch(
        self,
        account,
        endpoint,
        json=None,
        data=None,
        headers=None,
    ):
        """
        Executes PATCH request.
        """

        return self._request(
            account,
            "PATCH",
            endpoint,
            json=json,
            data=data,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------------

    def delete(
        self,
        account,
        endpoint,
        headers=None,
    ):
        """
        Executes DELETE request.
        """

        return self._request(
            account,
            "DELETE",
            endpoint,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # Multipart POST
    # -------------------------------------------------------------------------

    def post_multipart(
        self,
        account,
        endpoint,
        *,
        files,
        data=None,
        headers=None,
    ):
        """
        Uploads multipart/form-data.
        """

        return self._request(
            account,
            "POST",
            endpoint,
            files=files,
            data=data,
            headers=headers,
        )

    # -------------------------------------------------------------------------
    # Download
    # -------------------------------------------------------------------------

    def download(
        self,
        account,
        endpoint,
    ):
        """
        Downloads binary content.
        """

        url = self._url(endpoint)

        response = requests.get(
            url,
            headers=self._headers(account),
            timeout=self._settings()["timeout"],
        )

        response.raise_for_status()

        return response.content

    # -------------------------------------------------------------------------
    # Ping
    # -------------------------------------------------------------------------

    def ping(
        self,
        account,
    ):
        """
        Tests API availability.
        """

        try:

            self.get(
                account,
                "/users/me",
            )

            return True

        except Exception:

            _logger.exception(
                "Mercado Libre API is unavailable."
            )

            return False

    # -------------------------------------------------------------------------
    # Current User
    # -------------------------------------------------------------------------

    def me(
        self,
        account,
    ):
        """
        Returns authenticated user.
        """

        return self.get(
            account,
            "/users/me",
        )

    # -------------------------------------------------------------------------
    # OAuth Validation
    # -------------------------------------------------------------------------

    def oauth_test(
        self,
        account,
    ):
        """
        Tests OAuth credentials.
        """

        try:

            user = self.me(account)

            return {

                "success": True,

                "user": user,

            }

        except Exception as error:

            return {

                "success": False,

                "error": str(error),

            }

    # -------------------------------------------------------------------------
    # API Version
    # -------------------------------------------------------------------------

    def api_version(self):
        """
        Returns current API version.
        """

        return "v1"

    # -------------------------------------------------------------------------
    # Base URL
    # -------------------------------------------------------------------------

    def base_url(self):
        """
        Returns API base URL.
        """

        return self.BASE_URL