# -*- coding: utf-8 -*-
import json
import logging

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

        account = request.env["sce.account"].sudo().search(
            [("active", "=", True), ("connector_id.provider_type", "=", provider_key)],
            limit=1,
        )
        if not account:
            return {"ok": False, "error": f"no active account for provider '{provider_key}'"}

        expected = False
        if account.credentials_json:
            try:
                credentials = json.loads(account.credentials_json)
                expected = credentials.get("webhook_token")
            except Exception:
                expected = False

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