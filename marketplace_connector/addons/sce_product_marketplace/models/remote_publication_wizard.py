# -*- coding: utf-8 -*-
import json

from odoo import fields, models
from odoo.exceptions import UserError


class RemotePublicationWizard(models.TransientModel):
    _name = "marketplace.remote.publication.wizard"
    _description = "Publicación remota de productos"

    account_id = fields.Many2one(
        "sce.account",
        string="Cuenta Marketplace",
        required=True,
        domain="[('provider_type', '!=', 'odoo'), ('state', '=', 'connected'), ('active', '=', True)]",
    )
    provider_type = fields.Selection(related="account_id.provider_type", readonly=True)
    search_query = fields.Char(string="Buscar en Odoo")
    default_category_id = fields.Char(string="Categoría predeterminada")
    default_listing_type = fields.Char(string="Tipo de publicación", default="gold_special")
    default_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
        default="new",
    )
    default_shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        string="Envío",
        default="me2",
    )
    line_ids = fields.One2many(
        "marketplace.remote.publication.wizard.line", "wizard_id", string="Productos remotos"
    )
    selected_count = fields.Integer(compute="_compute_selected_count")

    def _compute_selected_count(self):
        for wizard in self:
            wizard.selected_count = len(wizard.line_ids.filtered("selected"))

    def action_search_remote_products(self):
        self.ensure_one()
        if not self.account_id.odoo_base_url:
            raise UserError("Primero configurá y validá la conexión con el Odoo del cliente.")

        query = (self.search_query or "").strip()
        domain = [("active", "=", True), ("sale_ok", "=", True)]
        if query:
            domain += [
                "|", "|",
                ("name", "ilike", query),
                ("default_code", "ilike", query),
                ("barcode", "ilike", query),
            ]
        products = self.account_id._fetch_remote_odoo_records(
            "product.product",
            domain=domain,
            fields_to_read=[
                "id", "display_name", "name", "default_code", "barcode",
                "virtual_available", "list_price", "taxes_id",
            ],
        )
        self.line_ids.unlink()
        lines = []
        for product in products:
            sku = product.get("default_code") or ""
            barcode = product.get("barcode") or ""
            mapping = self.env["marketplace.product.mapping"]
            if sku or barcode:
                mapping_domain = [("account_id", "=", self.account_id.id)]
                mapping_domain += [("sku", "=", sku)] if sku else [("barcode", "=", barcode)]
                mapping = mapping.sudo().search(mapping_domain, limit=1)
            base_price = self.account_id._get_remote_pricelist_price(
                product["id"], product.get("list_price") or 0.0
            )
            price_with_tax = self.account_id._get_remote_price_with_tax(
                base_price, product.get("taxes_id") or []
            )
            lines.append((0, 0, {
                "selected": not bool(mapping),
                "remote_product_id": product["id"],
                "name": product.get("display_name") or product.get("name") or "Producto",
                "title": product.get("name") or product.get("display_name") or "Producto",
                "sku": sku,
                "barcode": barcode,
                "forecast_stock": product.get("virtual_available") or 0.0,
                "base_price": price_with_tax,
                "category_id": self.default_category_id,
                "listing_type": self.default_listing_type or "gold_special",
                "condition": self.default_condition,
                "shipping_mode": self.default_shipping_mode,
                "existing_external_id": mapping.external_id if mapping else False,
                "state": "mapped" if mapping else "ready",
            }))
        self.write({"line_ids": lines})
        return self._reopen()

    def action_apply_defaults(self):
        self.ensure_one()
        values = {
            "category_id": self.default_category_id,
            "listing_type": self.default_listing_type or "gold_special",
            "condition": self.default_condition,
            "shipping_mode": self.default_shipping_mode,
        }
        self.line_ids.filtered("selected").write(values)
        return self._reopen()

    def action_select_all(self):
        self.line_ids.write({"selected": True})
        return self._reopen()

    def action_clear_selection(self):
        self.line_ids.write({"selected": False})
        return self._reopen()

    def action_publish_selected(self):
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        if not selected:
            raise UserError("Seleccioná al menos un producto para publicar.")

        provider = self.env["sce.provider.factory"].get_provider(self.account_id)
        succeeded = 0
        failed = 0
        for line in selected:
            try:
                line._publish_remote(provider)
                succeeded += 1
            except Exception as err:
                line.write({"state": "error", "error_message": str(err)})
                failed += 1
        message = f"{succeeded} producto(s) publicados o actualizados."
        if failed:
            message += f" {failed} requieren revisión; consultá el detalle en la tabla."
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Publicación remota finalizada",
                "message": message,
                "type": "warning" if failed else "success",
                "sticky": bool(failed),
                "next": self._reopen(),
            },
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Publicación remota",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class RemotePublicationWizardLine(models.TransientModel):
    _name = "marketplace.remote.publication.wizard.line"
    _description = "Producto remoto para publicar"
    _order = "name"

    wizard_id = fields.Many2one(
        "marketplace.remote.publication.wizard", required=True, ondelete="cascade"
    )
    selected = fields.Boolean(default=True)
    remote_product_id = fields.Integer(string="ID Odoo", required=True)
    name = fields.Char(readonly=True)
    title = fields.Char(string="Título", required=True)
    sku = fields.Char(string="SKU", readonly=True)
    barcode = fields.Char(string="Código de Barras", readonly=True)
    forecast_stock = fields.Float(string="Stock pronosticado", readonly=True)
    base_price = fields.Float(string="Precio con impuestos", readonly=True)
    category_id = fields.Char(string="Categoría")
    listing_type = fields.Char(string="Tipo publicación", default="gold_special", required=True)
    condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        default="new",
        required=True,
    )
    shipping_mode = fields.Selection(
        [("me2", "Mercado Envíos"), ("custom", "Acordar con comprador"), ("not_specified", "No especificado")],
        default="me2",
        required=True,
    )
    attributes_json = fields.Text(string="Atributos JSON", default="[]")
    picture_url = fields.Char(string="URL imagen")
    existing_external_id = fields.Char(string="ID existente", readonly=True)
    state = fields.Selection(
        [("ready", "Listo"), ("mapped", "Ya publicado"), ("done", "Publicado"), ("error", "Error")],
        default="ready",
        readonly=True,
    )
    error_message = fields.Text(readonly=True)

    def _publish_remote(self, provider):
        self.ensure_one()
        if not self.category_id:
            raise UserError("Seleccioná una categoría antes de publicar.")
        try:
            attributes = json.loads(self.attributes_json or "[]")
        except (TypeError, ValueError) as err:
            raise UserError(f"Atributos JSON inválidos: {err}") from err
        if not isinstance(attributes, list):
            raise UserError("Atributos JSON debe contener una lista.")

        account = self.wizard_id.account_id
        price = account.calculate_marketplace_price(self.base_price)
        quantity = account.calculate_marketplace_stock(self.forecast_stock)
        pictures = [{"source": self.picture_url.strip()}] if (self.picture_url or "").strip() else []
        payload = {
            "title": self.title,
            "category_id": self.category_id,
            "listing_type": self.listing_type,
            "listing_type_id": self.listing_type,
            "condition": self.condition,
            "shipping_mode": self.shipping_mode,
            "price": price,
            "available_quantity": quantity,
            "stock": quantity,
            "attributes": attributes,
            "pictures": pictures,
            "seller_custom_field": self.sku or self.barcode,
            "provider_data": {"remote_product_id": self.remote_product_id},
        }
        if self.existing_external_id:
            payload.update({
                "external_id": self.existing_external_id,
                "id": self.existing_external_id,
                "item_id": self.existing_external_id,
            })
            result = provider.update_product(payload) or {}
            external_id = self.existing_external_id
        else:
            result = provider.publish_product(payload) or {}
            external_id = result.get("item_id") or result.get("external_id")
        if not external_id:
            raise UserError("El marketplace no devolvió el ID externo del producto publicado.")

        mapping_model = self.env["marketplace.product.mapping"].sudo()
        mapping = mapping_model.search([
            ("account_id", "=", account.id),
            ("external_id", "=", str(external_id)),
        ], limit=1)
        values = {
            "account_id": account.id,
            "external_id": str(external_id),
            "sku": self.sku or False,
            "barcode": self.barcode or False,
            "remote_only": True,
            "last_synced_price": price,
        }
        if mapping:
            mapping.write(values)
        else:
            mapping_model.create(values)
        self.write({
            "existing_external_id": str(external_id),
            "state": "done",
            "error_message": False,
        })
        return result
