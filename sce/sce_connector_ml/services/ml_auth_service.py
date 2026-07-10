# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Authentication Service
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from odoo import api

from odoo.addons.sce_base.services.http.auth import BearerAuth

from ..services.ml_api_client import MLApiClient


class MLAuthService:
    """
    Mercado Libre OAuth service.
    """

    def __init__(
        self,
        env,
    ) -> None:

        self.env = env

    # ==========================================================
    # Public API
    # ==========================================================

    def authorize(
        self,
        account,
        code: str,
    ) -> dict[str, Any]:
        """
        Exchanges the authorization code for an access token.
        """

        client = self._oauth_client(account)

        token = client.exchange_token(
            client_id=account.client_id,
            client_secret=account.client_secret,
            code=code,
            redirect_uri=account.redirect_uri,
        )

        self._store_token(
            account,
            token,
        )

        self._load_user_information(account)

        account.write({
            "connected": True,
        })

        return token

    def refresh(
        self,
        account,
    ) -> dict[str, Any]:
        """
        Refresh access token.
        """

        credential = self._credential(account)

        token = self._oauth_client(account).refresh_token(
            client_id=account.client_id,
            client_secret=account.client_secret,
            refresh_token=credential.refresh_token,
        )

        self._store_token(
            account,
            token,
        )

        return token

    def disconnect(
        self,
        account,
    ) -> None:
        """
        Disconnect account.
        """

        credential = self._credential(account)

        if credential:
            credential.unlink()

        account.write({
            "connected": False,
            "seller_id": False,
            "seller_nickname": False,
            "user_id": False,
        })

    def authenticated_client(
        self,
        account,
    ) -> MLApiClient:
        """
        Returns an authenticated API client.
        """

        credential = self.ensure_valid_token(account)

        auth = BearerAuth(
            credential.access_token,
        )

        return MLApiClient(
            base_url=account.site_id.api_base_url,
            auth=auth,
        )

    def ensure_valid_token(
        self,
        account,
    ):
        """
        Returns a valid credential.
        """

        credential = self._credential(account)

        if credential is None:
            raise ValueError(
                "Mercado Libre account is not authenticated."
            )

        if self._is_expired(credential):

            self.refresh(account)

            credential.invalidate_cache()

            credential = self._credential(account)

        return credential

    # ==========================================================
    # Helpers
    # ==========================================================

    def _oauth_client(
        self,
        account,
    ) -> MLApiClient:

        return MLApiClient(
            base_url=account.site_id.auth_base_url,
        )

    def _credential(
        self,
        account,
    ):

        return self.env["sce.credential"].search(
            [
                ("account_id", "=", account.account_id.id),
                ("provider", "=", "mercadolibre"),
            ],
            limit=1,
        )

    def _store_token(
        self,
        account,
        token: dict[str, Any],
    ) -> None:

        credential = self._credential(account)

        expires_at = datetime.utcnow() + timedelta(
            seconds=token["expires_in"]
        )

        values = {
            "account_id": account.account_id.id,
            "provider": "mercadolibre",
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "token_type": token.get(
                "token_type",
                "Bearer",
            ),
            "expires_at": expires_at,
        }

        if credential:
            credential.write(values)
        else:
            self.env["sce.credential"].create(values)

                # ==========================================================
    # User Information
    # ==========================================================

    def _load_user_information(
        self,
        account,
    ) -> None:
        """
        Loads Mercado Libre user information and stores it
        into the connector account.
        """

        client = self.authenticated_client(account)

        user = client.get_me()

        values = {
            "connected": True,
            "seller_id": str(user.get("id") or ""),
            "seller_nickname": user.get("nickname"),
            "user_id": str(user.get("id") or ""),
        }

        account.write(values)

    # ==========================================================
    # Token Validation
    # ==========================================================

    def token_is_valid(
        self,
        account,
    ) -> bool:
        """
        Returns True when the account has a valid token.
        """

        credential = self._credential(account)

        if not credential:
            return False

        if not credential.access_token:
            return False

        if self._is_expired(credential):
            return False

        return True

    def expires_in(
        self,
        account,
    ) -> int:
        """
        Returns remaining token lifetime in seconds.
        """

        credential = self._credential(account)

        if credential is None:
            return 0

        if credential.expires_at is None:
            return 0

        now = datetime.utcnow()

        delta = credential.expires_at - now

        return max(
            int(delta.total_seconds()),
            0,
        )

    def token_information(
        self,
        account,
    ) -> dict[str, Any]:
        """
        Returns credential metadata.
        """

        credential = self._credential(account)

        if credential is None:
            return {}

        return {
            "provider": credential.provider,
            "token_type": credential.token_type,
            "expires_at": credential.expires_at,
            "expires_in": self.expires_in(account),
            "valid": self.token_is_valid(account),
        }

    # ==========================================================
    # Account Synchronization
    # ==========================================================

    def synchronize_account(
        self,
        account,
    ) -> dict[str, Any]:
        """
        Synchronizes account information from Mercado Libre.
        """

        client = self.authenticated_client(account)

        user = client.get_me()

        account.write({
            "seller_id": str(user.get("id") or ""),
            "seller_nickname": user.get("nickname"),
            "user_id": str(user.get("id") or ""),
        })

        return user

    # ==========================================================
    # Credential Helpers
    # ==========================================================

    @staticmethod
    def _is_expired(
        credential,
    ) -> bool:
        """
        Checks whether the credential has expired.
        """

        if not credential.expires_at:
            return True

        # Se renueva un minuto antes para evitar
        # problemas con diferencias de reloj.
        limit = datetime.utcnow() + timedelta(seconds=60)

        return credential.expires_at <= limit

    def revoke(
        self,
        account,
    ) -> None:
        """
        Removes locally stored OAuth credentials.
        """

        credential = self._credential(account)

        if credential:
            credential.unlink()

        account.write({
            "connected": False,
        })

    def reconnect(
        self,
        account,
        code: str,
    ) -> dict[str, Any]:
        """
        Re-authorizes an existing account.
        """

        self.revoke(account)

        return self.authorize(
            account,
            code,
        )

            # ==========================================================
    # OAuth URL
    # ==========================================================

    def authorization_url(
        self,
        account,
        state: str | None = None,
    ) -> str:
        """
        Builds Mercado Libre OAuth authorization URL.
        """

        params = [
            ("response_type", "code"),
            ("client_id", account.client_id),
            ("redirect_uri", account.redirect_uri),
        ]

        if state:
            params.append(("state", state))

        query = "&".join(
            f"{key}={value}"
            for key, value in params
            if value
        )

        base = account.site_id.auth_base_url.rstrip("/")

        return f"{base}/authorization?{query}"

    # ==========================================================
    # Connection Status
    # ==========================================================

    def is_connected(
        self,
        account,
    ) -> bool:
        """
        Returns True if the account is connected.
        """

        return self.token_is_valid(account)

    def connection_information(
        self,
        account,
    ) -> dict[str, Any]:
        """
        Returns connection information.
        """

        credential = self._credential(account)

        return {
            "connected": self.token_is_valid(account),
            "seller_id": account.seller_id,
            "seller_nickname": account.seller_nickname,
            "user_id": account.user_id,
            "credential": credential,
            "expires_in": self.expires_in(account),
        }

    # ==========================================================
    # Validation
    # ==========================================================

    def validate_connection(
        self,
        account,
    ) -> bool:
        """
        Validates the current OAuth session by requesting
        the authenticated user.
        """

        try:

            client = self.authenticated_client(account)

            client.get_me()

            return True

        except Exception:

            return False

    # ==========================================================
    # Factory
    # ==========================================================

    def bearer_auth(
        self,
        account,
    ) -> BearerAuth:
        """
        Returns a BearerAuth instance for the account.
        """

        credential = self.ensure_valid_token(account)

        return BearerAuth(
            credential.access_token,
        )

    def api_client(
        self,
        account,
    ) -> MLApiClient:
        """
        Returns an authenticated Mercado Libre API client.
        """

        return MLApiClient(
            base_url=account.site_id.api_base_url,
            auth=self.bearer_auth(account),
        )

    # ==========================================================
    # Health Check
    # ==========================================================

    def ping(
        self,
        account,
    ) -> bool:
        """
        Performs a lightweight connectivity check.
        """

        try:

            self.api_client(account).get_me()

            return True

        except Exception:

            return False