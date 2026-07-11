# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class SceWebhookController(http.Controller):

    @http.route(
        ["/sce/webhook/<string:provider>"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def sce_webhook(self, provider, **kwargs):
        payload = request.jsonrequest or {}
        token = request.httprequest.headers.get("X-SCE-Webhook-Token")

        if not token:
            return {"ok": False, "error": "missing webhook token"}

        account = request.env["sce.account"].sudo().search(
            [("active", "=", True), ("connector_id.provider_type", "=", provider)],
            limit=1,
        )
        if not account:
            return {"ok": False, "error": f"no active account for provider '{provider}'"}

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
            name=f"Webhook received ({provider})",
            event_type="WebhookReceived",
            connector=account.connector_id,
            account=account,
            payload=payload,
            company=account.company_id,
        )

        log_service = request.env["sce.log.service"].sudo()
        log_service.log(
            name="Webhook received",
            message=f"Webhook received for provider {provider}",
            level="INFO",
            connector=account.connector_id,
            account=account,
            details_json=json.dumps(payload),
        )

        return {"ok": True, "event_id": event.id}