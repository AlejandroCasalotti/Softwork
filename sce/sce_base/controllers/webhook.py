# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Webhook Controller
"""

from __future__ import annotations

import json

from odoo import http
from odoo.http import request


class SCEWebhookController(http.Controller):
    """
    Generic webhook endpoint used by all SCE connectors.
    """

    # -------------------------------------------------------------------------
    # Webhook Receiver
    # -------------------------------------------------------------------------

    @http.route(
        "/sce/webhook/<string:connector_code>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_receiver(
        self,
        connector_code,
        **kwargs,
    ):
        """
        Receives webhook notifications from external marketplaces.
        """

        try:

            payload = json.loads(
                request.httprequest.data or b"{}"
            )

        except Exception:

            payload = {
                "raw": request.httprequest.data.decode(
                    "utf-8",
                    errors="ignore",
                )
            }

        headers = dict(request.httprequest.headers)

        Connector = request.env["sce.connector"].sudo()

        connector = Connector.search(
            [
                ("code", "=", connector_code),
            ],
            limit=1,
        )

        if not connector:

            return request.make_json_response(
                {
                    "success": False,
                    "message": "Connector not found.",
                },
                status=404,
            )

        account = request.env[
            "sce.account"
        ].sudo().search(
            [
                ("connector_id", "=", connector.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not account:

            return request.make_json_response(
                {
                    "success": False,
                    "message": "No active account configured.",
                },
                status=404,
            )

        webhook = request.env[
            "sce.webhook"
        ].sudo().create(
            {
                "account_id": account.id,
                "event": headers.get(
                    "X-Event-Type",
                    "unknown",
                ),
                "payload": payload,
                "headers": headers,
                "signature": headers.get(
                    "X-Hub-Signature"
                ),
                "source_ip": request.httprequest.remote_addr,
                "user_agent": headers.get(
                    "User-Agent"
                ),
            }
        )

        webhook.process()

        return request.make_json_response(
            {
                "success": True,
                "webhook_id": webhook.id,
                "state": webhook.state,
            }
        )