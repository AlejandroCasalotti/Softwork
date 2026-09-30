# -*- coding: utf-8 -*-
import json
import logging
import hmac

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class SceWebhookController(http.Controller):

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

        seller_id = payload.get("user_id") or payload.get("seller_id")
        if isinstance(payload.get("user"), dict):
            seller_id = seller_id or payload["user"].get("id")
        if not seller_id:
            return {"ok": False, "error": "missing seller identity"}

        accounts = request.env["sce.account"].sudo().search(
            [
                ("active", "=", True),
                ("state", "=", "connected"),
                ("provider_type", "=", provider_key),
                ("external_user_id", "=", str(seller_id)),
            ],
            limit=2,
        )
        if len(accounts) != 1:
            return {"ok": False, "error": "account not found or seller identity is ambiguous"}
        account = accounts

        expected = False
        if account.credentials_json:
            try:
                credentials = json.loads(account.credentials_json)
                expected = credentials.get("webhook_token")
            except Exception:
                expected = False

        if not expected:
            return {"ok": False, "error": "webhook authentication is not configured"}
        if not hmac.compare_digest(str(token).encode("utf-8"), str(expected).encode("utf-8")):
            return {"ok": False, "error": "invalid webhook token"}

        event = request.env["sce.event"].sudo().emit_event(
            name=f"Webhook received ({provider_key})",
            event_type="WebhookReceived",
            connector=account.connector_id,
            account=account,
            payload={
                "topic": payload.get("topic") or payload.get("type"),
                "resource": payload.get("resource"),
                "user_id": str(seller_id),
            },
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
        )

        return {
            "ok": True,
            "event_id": event.id,
            "provider": provider_key,
            "sync_job_id": sync_job.id if sync_job else False,
        }