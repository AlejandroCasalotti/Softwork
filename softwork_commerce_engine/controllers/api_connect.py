# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class SceApiConnectController(http.Controller):

    def _json_error(self, message, status=400):
        body = json.dumps({"ok": False, "error": message})
        return request.make_response(body, headers=[("Content-Type", "application/json")], status=status)

    def _json_ok(self, payload, status=200):
        body = json.dumps({"ok": True, **payload})
        return request.make_response(body, headers=[("Content-Type", "application/json")], status=status)

    def _resolve_account(self, payload):
        account_id = payload.get("account_id")
        external_ref = payload.get("external_account_ref")
        domain = []
        if account_id:
            domain = [("id", "=", int(account_id))]
        elif external_ref:
            domain = [("external_account_ref", "=", external_ref)]
        else:
            return None
        return request.env["sce.account"].sudo().search(domain, limit=1)

    @http.route(
        ["/sce/api/v1/mercadolibre/connect/start"],
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def api_ml_connect_start(self, **kwargs):
        payload = request.jsonrequest or {}
        account = self._resolve_account(payload)
        if not account:
            return self._json_error("Account not found", 404)
        if account.connector_id.provider_type != "mercadolibre":
            return self._json_error("Only mercadolibre provider is supported in this endpoint", 400)
        if not account.client_id or not account.redirect_uri:
            return self._json_error("Missing OAuth configuration: client_id/redirect_uri", 400)

        return self._json_ok(
            {
                "account_id": account.id,
                "state": account.state,
                "oauth_url": account.oauth_url,
            }
        )

    @http.route(
        ["/sce/api/v1/mercadolibre/connect/callback"],
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def api_ml_connect_callback(self, **kwargs):
        payload = request.jsonrequest or {}
        account = self._resolve_account(payload)
        if not account:
            return self._json_error("Account not found", 404)

        error = payload.get("error")
        code = payload.get("code")

        if error:
            account.write({"state": "error", "last_error": f"OAuth error: {error}"})
            return self._json_ok({"account_id": account.id, "state": account.state, "message": str(account.last_error)})

        if not code:
            return self._json_error("Missing code", 400)

        account.auth_code = code
        try:
            account.action_exchange_code()
        except Exception as err:
            account.write({"state": "error", "last_error": str(err)})
            return self._json_error(str(err), 400)

        return self._json_ok(
            {
                "account_id": account.id,
                "state": account.state,
                "connected": account.state == "connected",
                "external_user_id": account.external_user_id or "",
            }
        )

    @http.route(
        ["/sce/api/v1/mercadolibre/connect/status"],
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def api_ml_connect_status(self, **kwargs):
        payload = request.jsonrequest or {}
        account = self._resolve_account(payload)
        if not account:
            return self._json_error("Account not found", 404)

        return self._json_ok(
            {
                "account_id": account.id,
                "state": account.state,
                "connected": account.state == "connected",
                "external_user_id": account.external_user_id or "",
                "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
                "last_error": account.last_error or "",
            }
        )