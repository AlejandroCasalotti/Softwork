# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models


class SceEvent(models.Model):
    _name = "sce.event"
    _description = "SCE Event"
    _order = "create_date desc"

    name = fields.Char(required=True, index=True)
    event_type = fields.Selection(
        selection=[
            ("ProductCreated", "ProductCreated"),
            ("ProductUpdated", "ProductUpdated"),
            ("ProductDeleted", "ProductDeleted"),
            ("PriceChanged", "PriceChanged"),
            ("StockChanged", "StockChanged"),
            ("OrderImported", "OrderImported"),
            ("OrderCancelled", "OrderCancelled"),
            ("ShipmentCreated", "ShipmentCreated"),
            ("ShipmentDelivered", "ShipmentDelivered"),
            ("PaymentApproved", "PaymentApproved"),
            ("PaymentRejected", "PaymentRejected"),
            ("WebhookReceived", "WebhookReceived"),
            ("JobStarted", "JobStarted"),
            ("JobFinished", "JobFinished"),
            ("JobFailed", "JobFailed"),
            ("OAuthRefreshed", "OAuthRefreshed"),
            ("ConnectionLost", "ConnectionLost"),
            ("ConnectionRecovered", "ConnectionRecovered"),
        ],
        required=True,
        index=True,
    )
    connector_id = fields.Many2one("sce.connector", ondelete="set null", index=True)
    account_id = fields.Many2one("sce.account", ondelete="set null", index=True)
    job_id = fields.Many2one("sce.job", ondelete="set null", index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    payload_json = fields.Text()

    @api.model
    def emit_event(self, *, name, event_type, connector=None, account=None, job=None, payload=None, company=None):
        payload_json = payload if isinstance(payload, str) else json.dumps(payload or {})
        return self.create({
            "name": name,
            "event_type": event_type,
            "connector_id": connector.id if connector else False,
            "account_id": account.id if account else False,
            "job_id": job.id if job else False,
            "company_id": company.id if company else (account.company_id.id if account else self.env.company.id),
            "payload_json": payload_json,
        })