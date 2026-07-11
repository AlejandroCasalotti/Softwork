# -*- coding: utf-8 -*-
from odoo import fields, models


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