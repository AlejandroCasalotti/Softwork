# -*- coding: utf-8 -*-
import base64
import logging
import re

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ml_order_id = fields.Char(string="ML Order ID", index=True, copy=False)
    ml_account_id = fields.Many2one("sw.ml.account", string="Cuenta ML", copy=False)

    def _normalize_vat(self, value):
        return re.sub(r"\D+", "", value or "")

    def _extract_buyer_doc(self, buyer):
        buyer = buyer or {}
        doc = buyer.get("doc_number") or buyer.get("docNumber")
        if doc:
            return str(doc)
        billing = buyer.get("billing_info") or {}
        doc = billing.get("doc_number") or billing.get("docNumber")
        if doc:
            return str(doc)
        return ""

    def _find_or_create_partner_from_ml(self, order_data):
        buyer = order_data.get("buyer") or {}
        shipping = order_data.get("shipping") or {}
        receiver = (shipping.get("receiver_address") or {}) if isinstance(shipping, dict) else {}

        doc = self._extract_buyer_doc(buyer)
        norm_doc = self._normalize_vat(doc)
        partner = False
        if norm_doc:
            partner = self.env["res.partner"].search([("vat", "!=", False)], limit=1).filtered(
                lambda p: self._normalize_vat(p.vat) == norm_doc
            )[:1]

        if partner:
            return partner

        name = buyer.get("nickname") or buyer.get("first_name") or "Cliente MercadoLibre"
        if buyer.get("last_name"):
            name = f"{name} {buyer.get('last_name')}".strip()

        vals = {
            "name": name,
            "email": buyer.get("email"),
            "phone": buyer.get("phone", {}).get("number") if isinstance(buyer.get("phone"), dict) else False,
            "street": receiver.get("address_line"),
            "city": receiver.get("city", {}).get("name") if isinstance(receiver.get("city"), dict) else False,
            "zip": receiver.get("zip_code"),
            "vat": doc or False,
            "customer_rank": 1,
        }
        return self.env["res.partner"].create({k: v for k, v in vals.items() if v})

    def _resolve_product_from_integration(self, integration, item_data):
        item_data = item_data or {}
        ml_item_id = item_data.get("id")
        if ml_item_id:
            product = self.env["product.product"].search(
                [("product_tmpl_id.ml_item_id", "=", ml_item_id)],
                limit=1,
            )
            if product:
                return product

        match_mode = (integration.odoo_match_field if integration else "default_code") or "default_code"
        sku = item_data.get("seller_sku") or item_data.get("sku")
        barcode = item_data.get("barcode")
        odoo_product_id = item_data.get("odoo_product_id") or item_data.get("id_odoo")

        if match_mode == "id" and odoo_product_id:
            try:
                product = self.env["product.product"].browse(int(odoo_product_id))
                if product.exists():
                    return product
            except Exception:
                pass

        if match_mode == "barcode" and barcode:
            product = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
            if product:
                return product

        if match_mode == "default_code" and sku:
            product = self.env["product.product"].search([("default_code", "=", sku)], limit=1)
            if product:
                return product

        return self.env["product.product"].search([], limit=1)

    def _get_or_create_ml_team(self, company=None):
        domain = [("name", "=", "Mercado Libre")]
        if company:
            domain.append(("company_id", "in", [False, company.id]))
        team = self.env["crm.team"].search(domain, limit=1)
        if team:
            return team
        vals = {"name": "Mercado Libre"}
        if company:
            vals["company_id"] = company.id
        return self.env["crm.team"].create(vals)

    def _attach_ml_label_if_available(self, sale, account, order_data):
        shipping = order_data.get("shipping") or {}
        if not isinstance(shipping, dict):
            return
        label_url = shipping.get("label_url") or shipping.get("label", {}).get("url")
        if not label_url:
            return
        try:
            if not account:
                return
            response = account._ml_request("GET", label_url, with_auth=True)
            payload = response if isinstance(response, (bytes, bytearray)) else str(response).encode("utf-8")
            attachment = self.env["ir.attachment"].create({
                "name": f"ML_Label_{sale.ml_order_id}.txt",
                "type": "binary",
                "datas": base64.b64encode(payload),
                "res_model": "sale.order",
                "res_id": sale.id,
                "mimetype": "text/plain",
            })
            if sale.picking_ids:
                attachment.copy({
                    "res_model": "stock.picking",
                    "res_id": sale.picking_ids[0].id,
                })
        except Exception as err:
            _logger.warning("No se pudo adjuntar etiqueta ML en %s: %s", sale.display_name, err)

    def action_ml_import_orders(self, account=None, integration=None):
        if not account:
            account = self.env["sw.ml.account"].search([("active", "=", True)], limit=1)
        if not account or not account.seller_id:
            return {"created": 0, "skipped": 0, "errors": 0}

        try:
            data = account._ml_request(
                "GET",
                "/orders/search",
                params={"seller": account.seller_id, "sort": "date_desc"},
            )
        except Exception as err:
            _logger.exception("Error obteniendo órdenes de MercadoLibre: %s", err)
            return {"created": 0, "skipped": 0, "errors": 1}

        stats = {"created": 0, "skipped": 0, "errors": 0}
        results = (data or {}).get("results", [])
        for order_data in results:
            try:
                ml_order_id = str(order_data.get("id") or "")
                if not ml_order_id:
                    stats["skipped"] += 1
                    continue
                existing = self.search([("ml_order_id", "=", ml_order_id)], limit=1)
                if existing:
                    stats["skipped"] += 1
                    continue

                partner = self._find_or_create_partner_from_ml(order_data)
                company = integration.odoo_company_id if integration and integration.odoo_company_id else self.env.company
                team = self._get_or_create_ml_team(company=company)

                vals = {
                    "partner_id": partner.id,
                    "ml_order_id": ml_order_id,
                    "ml_account_id": account.id,
                    "origin": f"MercadoLibre {ml_order_id}",
                    "company_id": company.id,
                    "team_id": team.id,
                }
                if integration and integration.odoo_user_id:
                    vals["user_id"] = integration.odoo_user_id.id
                if integration and integration.odoo_warehouse_id:
                    vals["warehouse_id"] = integration.odoo_warehouse_id.id

                shipping = order_data.get("shipping") or {}
                if integration and integration.autosync_delivery_date and isinstance(shipping, dict):
                    date_created = shipping.get("date_created")
                    if date_created:
                        vals["commitment_date"] = date_created.replace("T", " ").replace("Z", "")

                sale = self.create(vals)

                for item in order_data.get("order_items", []):
                    i = item.get("item") or {}
                    qty = float(item.get("quantity") or 0.0)
                    unit_price = float(item.get("unit_price") or 0.0)
                    title = i.get("title") or "Producto MercadoLibre"

                    product = self._resolve_product_from_integration(integration, i)

                    self.env["sale.order.line"].create({
                        "order_id": sale.id,
                        "product_id": product.id if product else False,
                        "name": title,
                        "product_uom_qty": qty if qty > 0 else 1.0,
                        "price_unit": unit_price,
                    })

                if integration and integration.autosync_labels:
                    self._attach_ml_label_if_available(sale, account, order_data)

                # Hook para fase facturación automática/manual con adjunto ML
                if integration and integration.autosync_invoices:
                    _logger.info("Hook facturación ML pendiente para orden %s", sale.name)

                stats["created"] += 1
            except Exception as err:
                stats["errors"] += 1
                _logger.exception("Error creando orden ML %s: %s", order_data, err)

        if integration:
            _logger.info("Integración %s import orders stats: %s", integration.display_name, stats)
        return stats

    @classmethod
    def cron_ml_import_orders(cls, env):
        integrations = env["sw.integration"].search([
            ("state", "=", "confirmed"),
            ("integration_type_id", "=", "meli"),
            ("sync_orders", "=", True),
        ])
        for integration in integrations:
            env["sale.order"].action_ml_import_orders(
                account=integration.meli_account_id,
                integration=integration,
            )