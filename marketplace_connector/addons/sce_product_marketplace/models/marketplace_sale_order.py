# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class MarketplaceSaleOrder(models.Model):
    _inherit = "sale.order"

    marketplace_external_order_id = fields.Char(string="ID orden externo", index=True, copy=False)
    marketplace_account_id = fields.Many2one(
        "sce.account", string="Cuenta marketplace", ondelete="set null", index=True, copy=False
    )
    marketplace_order_state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("paid", "Pagada"),
            ("shipped", "Enviada"),
            ("delivered", "Entregada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado marketplace",
        index=True,
        copy=False,
    )
    marketplace_external_status = fields.Char(string="Estado externo", copy=False)
    marketplace_sync_date = fields.Datetime(string="Última sincronización marketplace", copy=False)
    marketplace_shipping_status = fields.Char(string="Estado de envío externo", copy=False)
    marketplace_shipment_id = fields.Char(string="ID despacho externo", copy=False)
    marketplace_tracking_number = fields.Char(string="Tracking externo", copy=False)
    marketplace_shipping_sync_date = fields.Datetime(string="Última sync de envío", copy=False)

    _marketplace_order_unique = models.Constraint(
        "UNIQUE(marketplace_account_id, marketplace_external_order_id)",
        "La orden externa ya está vinculada a esta cuenta marketplace.",
    )

    def _apply_marketplace_transition(self):
        for order in self:
            account = order.marketplace_account_id
            if not account:
                continue
            if (
                order.marketplace_order_state == "paid"
                and account.marketplace_auto_confirm_paid
                and order.state == "draft"
            ):
                order.action_confirm()
            elif (
                order.marketplace_order_state == "cancelled"
                and account.marketplace_auto_cancelled
                and order.state not in ("cancel", "done")
            ):
                order.action_cancel()

    def _apply_marketplace_logistics(self, order_data):
        shipping = order_data.get("shipping") if isinstance(order_data.get("shipping"), dict) else {}
        if not shipping:
            return
        tracking = shipping.get("tracking_number") or shipping.get("tracking_id") or shipping.get("tracking")
        values = {
            "marketplace_shipping_status": shipping.get("status") or False,
            "marketplace_shipment_id": shipping.get("id") or shipping.get("shipment_id") or False,
            "marketplace_tracking_number": tracking or False,
            "marketplace_shipping_sync_date": fields.Datetime.now(),
        }
        self.write(values)
        for order in self:
            for picking in order.picking_ids.filtered(lambda record: record.state not in ("done", "cancel")):
                picking_values = {}
                if tracking and "carrier_tracking_ref" in picking._fields:
                    picking_values["carrier_tracking_ref"] = tracking
                if picking_values:
                    picking.write(picking_values)
                if (
                    str(shipping.get("status") or "").lower() in {"shipped", "in_transit", "ready_to_ship"}
                    and picking.state in ("draft", "confirmed")
                ):
                    try:
                        picking.action_assign()
                    except Exception:
                        continue

    def _emit_marketplace_state_event(self, previous_state=None, previous_shipping_status=None):
        event_types = {
            "paid": "PaymentApproved",
            "cancelled": "OrderCancelled",
            "shipped": "ShipmentCreated",
            "delivered": "ShipmentDelivered",
        }
        for order in self:
            state_changed = previous_state != order.marketplace_order_state
            shipping_changed = previous_shipping_status != order.marketplace_shipping_status
            if previous_state is not None and not state_changed and not shipping_changed:
                continue
            event_type = event_types.get(order.marketplace_order_state, "OrderImported")
            if not state_changed and shipping_changed:
                event_type = (
                    "ShipmentDelivered"
                    if order.marketplace_shipping_status == "delivered"
                    else "ShipmentCreated"
                )
            self.env["sce.event"].sudo().emit_event(
                name="Marketplace order %s" % (order.marketplace_external_order_id or order.name),
                event_type=event_type,
                account=order.marketplace_account_id,
                payload={
                    "order_id": order.id,
                    "external_order_id": order.marketplace_external_order_id,
                    "state": order.marketplace_order_state,
                    "shipping_status": order.marketplace_shipping_status,
                },
                company=order.company_id,
            )

    def _marketplace_pickings(self):
        self.ensure_one()
        if not self.marketplace_external_order_id:
            raise UserError("La orden no está vinculada a un marketplace.")
        pickings = self.picking_ids.filtered(lambda picking: picking.state != "cancel")
        if not pickings:
            raise UserError("La orden marketplace todavía no tiene entregas para operar.")
        return pickings

    def action_marketplace_reserve(self):
        for order in self:
            for picking in order._marketplace_pickings().filtered(
                lambda record: record.state in ("draft", "confirmed", "assigned")
            ):
                picking.action_assign()
        return True

    def action_marketplace_mark_shipped(self):
        for order in self:
            order._marketplace_pickings()
            order.write(
                {
                    "marketplace_shipping_status": "shipped",
                    "marketplace_shipping_sync_date": fields.Datetime.now(),
                }
            )
        return True

    def action_marketplace_validate_delivery(self):
        for order in self:
            pickings = order._marketplace_pickings()
            for picking in pickings.filtered(lambda record: record.state not in ("done", "cancel")):
                result = picking.button_validate()
                if isinstance(result, dict):
                    return result
            if all(picking.state == "done" for picking in pickings):
                order.write(
                    {
                        "marketplace_shipping_status": "delivered",
                        "marketplace_shipping_sync_date": fields.Datetime.now(),
                    }
                )
        return True