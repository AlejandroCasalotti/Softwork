# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class SceWebhookController(http.Controller):

    def _resolve_account(self, provider_key, payload, token):
        accounts = request.env["sce.account"].sudo().search(
            [("active", "=", True), ("connector_id.provider_type", "=", provider_key)]
        )
        seller_id = payload.get("user_id") or payload.get("seller_id")
        if isinstance(payload.get("user"), dict):
            seller_id = seller_id or payload["user"].get("id")

        if seller_id:
            identity_matches = accounts.filtered(
                lambda account: str(account.external_user_id or "") == str(seller_id)
                or str(
                    getattr(account.connect_mercadolibre_account_id, "seller_user_id", False)
                    if getattr(account, "connect_mercadolibre_account_id", False)
                    else ""
                ) == str(seller_id)
            )
            if len(identity_matches) == 1:
                return identity_matches

        token_matches = accounts.filtered(lambda account: self._webhook_token(account) == token)
        return token_matches if len(token_matches) == 1 else request.env["sce.account"]

    @staticmethod
    def _webhook_token(account):
        if not account.credentials_json:
            return False
        try:
            credentials = json.loads(account.credentials_json)
        except Exception:
            return False
        return credentials.get("webhook_token")

    @http.route(
        ["/sce/webhook/<string:provider>"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def sce_webhook(self, provider, **kwargs):
        allowed_providers = {"mercadolibre"}
        provider_key = (provider or "").strip().lower()
        payload = request.jsonrequest or {}
        token = request.httprequest.headers.get("X-SCE-Webhook-Token")

        if provider_key not in allowed_providers:
            return {"ok": False, "error": f"unsupported provider '{provider}'"}

        if not token:
            return {"ok": False, "error": "missing webhook token"}

        if not isinstance(payload, dict):
            payload = {"raw": payload}

        account = self._resolve_account(provider_key, payload, token)
        if not account:
            _logger.warning(
                "Webhook de %s no enrutable: no se identificó una única cuenta SCE.",
                provider_key,
            )
            return {"ok": False, "error": f"no uniquely routable account for provider '{provider_key}'"}

        expected = self._webhook_token(account)

        if expected and token != expected:
            return {"ok": False, "error": "invalid webhook token"}

        event = request.env["sce.event"].sudo().emit_event(
            name=f"Webhook received ({provider_key})",
            event_type="WebhookReceived",
            connector=account.connector_id,
            account=account,
            payload=payload,
            company=account.company_id,
        )

        sync_job = False
        try:
            sync_job = request.env["marketplace.publication.service"].sudo().handle_webhook(account, payload)
        except KeyError:
            # The generic marketplace addon is optional for the base webhook route.
            pass
        except Exception:
            _logger.exception("Error routing webhook to marketplace publication for account_id=%s", account.id)

        log_service = request.env["sce.log.service"].sudo()
        log_service.log(
            name="Webhook received",
            message=f"Webhook received for provider {provider_key}",
            level="INFO",
            connector=account.connector_id,
            account=account,
            details_json=json.dumps(payload),
        )

        return {
            "ok": True,
            "event_id": event.id,
            "provider": provider_key,
            "sync_job_id": sync_job.id if sync_job else False,
        }