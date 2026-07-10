# -*- coding: utf-8 -*-

from __future__ import annotations

import secrets
import urllib.parse
from typing import Dict, Optional


class OAuthClient:
    """
    Generic OAuth2 client.

    Provider-agnostic implementation used by all SCE connectors.
    """

    def __init__(self, http_client):
        self.http = http_client

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_state() -> str:
        """Generate a cryptographically secure OAuth state."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def build_authorization_url(
        authorization_url: str,
        client_id: str,
        redirect_uri: str,
        scope: str = "",
        state: Optional[str] = None,
        response_type: str = "code",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Build OAuth authorization URL.
        """
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": response_type,
        }

        if scope:
            params["scope"] = scope

        if state:
            params["state"] = state

        if extra_params:
            params.update(extra_params)

        return (
            authorization_url
            + "?"
            + urllib.parse.urlencode(params)
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def exchange_code(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ):
        """
        Exchange authorization code for an access token.
        """
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        response = self.http.post(
            token_url,
            json=payload,
        )

        return self.http.to_json(response)

    def refresh_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        """
        Refresh an expired access token.
        """
        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        response = self.http.post(
            token_url,
            json=payload,
        )

        return self.http.to_json(response)

    def revoke(
        self,
        revoke_url: str,
        access_token: str,
    ):
        """
        Revoke OAuth session.
        """
        payload = {
            "token": access_token,
        }

        response = self.http.post(
            revoke_url,
            json=payload,
        )

        return self.http.to_json(response)