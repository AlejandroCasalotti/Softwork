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
        env = request.env["sce.account"].with_user(request.env.user).sudo()
        domain = [("company_id", "in", request.env.user.company_ids.ids)]
        if account_id:
            try:
                account_id = int(account_id)
            except Exception:
                return None
            domain += [("id", "=", account_id)]
            return env.search(domain, limit=1)
        if external_ref:
            domain += [("external_account_ref", "=", external_ref)]
            return env.search(domain, limit=1)
        return None

    def _get_or_create_quick_ml_account(self):
        company = request.env.company
        return request.env["sce.account"].with_user(request.env.user).sudo().get_or_create_quick_ml_account(company=company)

    def _step_payload(self, account):
        if account.state == "connected":
            return {
                "step": "connected",
                "hint": "Cuenta conectada correctamente.",
                "next_action": "sync",
            }
        if account.state == "error":
            return {
                "step": "error",
                "hint": account.last_error or "Se produjo un error de conexión.",
                "next_action": "retry_connect",
            }
        return {
            "step": "authorize",
            "hint": "Redirigir al usuario a MercadoLibre para autorizar.",
            "next_action": "open_oauth_url",
        }

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
            account = self._get_or_create_quick_ml_account()

        if account.connector_id.provider_type != "mercadolibre":
            return self._json_error("Only mercadolibre provider is supported in this endpoint", 400)

        # Sincronizar credenciales de onboarding si existen
        account._sync_onboarding_to_oauth_fields()

        oauth_ready = bool(account.client_id and account.redirect_uri)
        oauth_url = False
        if oauth_ready:
            action = account.action_open_oauth_url()
            oauth_url = action.get("url")

        return self._json_ok(
            {
                "account_id": account.id,
                "state": account.state,
                "oauth_ready": oauth_ready,
                "oauth_url": oauth_url,
                "missing_fields": [] if oauth_ready else ["ml_client_id", "ml_client_secret", "ml_redirect_uri"],
                **self._step_payload(account),
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

        try:
            account.write({"auth_code": code})
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
                "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
                "last_error": account.last_error or "",
                **self._step_payload(account),
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
                **self._step_payload(account),
            }
        )