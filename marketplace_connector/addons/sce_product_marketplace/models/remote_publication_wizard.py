# -*- coding: utf-8 -*-
import json

from markupsafe import Markup

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
                "id", "product_tmpl_id", "categ_id", "display_name", "name",
                "default_code", "barcode", "virtual_available", "list_price",
                "standard_price", "taxes_id", "company_id",
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
                product["id"], product.get("list_price") or 0.0, product_data=product
            )
            price_with_tax = self.account_id._get_remote_price_with_tax(
                base_price,
                product.get("taxes_id") or [],
                company_id=product.get("company_id"),
            )
            lines.append((0, 0, {
                "selected": not bool(mapping),
                "remote_product_id": product["id"],
                "name": product.get("display_name") or product.get("name") or "Producto",
                "title": product.get("name") or product.get("display_name") or "Producto",
                "sku": sku,
                "barcode": barcode,
                "forecast_stock": product.get("virtual_available") or 0.0,
                "pricelist_price": base_price,
                "tax_amount": max(0.0, price_with_tax - base_price),
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
            "views": [(False, "form")],
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
    family_name = fields.Char(string="Familia / Línea")
    brand = fields.Char(string="Marca")
    model_name = fields.Char(string="Modelo")
    sku = fields.Char(string="SKU", readonly=True)
    barcode = fields.Char(string="Código de Barras", readonly=True)
    forecast_stock = fields.Float(string="Stock pronosticado", readonly=True)
    pricelist_price = fields.Float(string="Precio de lista", readonly=True)
    tax_amount = fields.Float(string="Impuestos", readonly=True)
    base_price = fields.Float(string="Precio con impuestos", readonly=True)
    account_rule_amount = fields.Float(string="Recargos de cuenta", compute="_compute_final_price")
    final_price = fields.Float(string="Precio antes de cuotas", compute="_compute_final_price")
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
    attribute_line_ids = fields.One2many(
        "marketplace.remote.publication.attribute.line", "publication_line_id", string="Atributos"
    )
    picture_url = fields.Char(string="URL imagen")
    existing_external_id = fields.Char(string="ID existente", readonly=True)
    state = fields.Selection(
        [("ready", "Listo"), ("mapped", "Ya publicado"), ("done", "Publicado"), ("error", "Error")],
        default="ready",
        readonly=True,
    )
    error_message = fields.Text(readonly=True)

    def _compute_final_price(self):
        for line in self:
            final_price = line.wizard_id.account_id.calculate_marketplace_price(
                line.base_price
            ) if line.wizard_id.account_id else line.base_price
            line.final_price = final_price
            line.account_rule_amount = final_price - line.base_price

    def action_open_configuration(self):
        self.ensure_one()
        view = self.env.ref(
            "sce_product_marketplace.view_remote_publication_wizard_line_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Completar publicación remota",
            "res_model": self._name,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "res_id": self.id,
            "target": "new",
        }

    def action_suggest_category(self):
        self.ensure_one()
        provider = self.env["sce.provider.factory"].get_provider(self.wizard_id.account_id)
        result = provider.search_categories(query=self.title or self.name, limit=8)
        categories = result.get("items") if isinstance(result, dict) else []
        if not categories:
            raise UserError("Mercado Libre no encontró una categoría sugerida para este producto.")
        category = categories[0]
        self.write({"category_id": category.get("category_id")})
        return self.action_load_required_attributes()

    def action_load_required_attributes(self):
        self.ensure_one()
        if not self.category_id:
            raise UserError("Ingresá o sugerí una categoría antes de cargar atributos.")
        provider = self.env["sce.provider.factory"].get_provider(self.wizard_id.account_id)
        result = provider.get_category_attributes(self.category_id)
        attributes = result.get("items") if isinstance(result, dict) else []
        self.attribute_line_ids.unlink()
        values = []
        for attribute in attributes or []:
            if not isinstance(attribute, dict) or not attribute.get("id"):
                continue
            is_required = bool(attribute.get("required"))
            is_conditional_required = bool(attribute.get("conditional_required"))
            is_gtin = attribute["id"] in ("GTIN", "EAN", "BARCODE")
            if not is_required and not is_conditional_required and not is_gtin:
                continue
            values.append((0, 0, {
                "attribute_id": attribute["id"],
                "attribute_name": attribute.get("name") or attribute["id"],
                "required": is_required or is_conditional_required,
                "value_type": attribute.get("value_type") or "string",
                "value_name": self.barcode if is_gtin and self.barcode else False,
                "allowed_values_json": json.dumps(attribute.get("values") or [], ensure_ascii=False),
            }))
        write_values = {"attribute_line_ids": values}
        if not self.family_name:
            write_values["family_name"] = self.title or self.name
        self.write(write_values)
        return {
            "type": "ir.actions.act_window",
            "name": "Completar publicación remota",
            "res_model": self._name,
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
            "target": "new",
        }

    def action_save_and_apply_defaults(self):
        self.ensure_one()
        self.wizard_id.write({
            "default_category_id": self.category_id,
            "default_listing_type": self.listing_type,
            "default_condition": self.condition,
            "default_shipping_mode": self.shipping_mode,
        })
        return {"type": "ir.actions.act_window_close"}

    def _publish_remote(self, provider):
        self.ensure_one()
        if not self.category_id:
            raise UserError("Seleccioná una categoría antes de publicar.")
        if not (self.sku or "").strip():
            raise UserError(
                "El producto necesita una Referencia Interna/SKU para publicarse y mantener la sincronización."
            )
        missing = self.attribute_line_ids.filtered(
            lambda attribute: attribute.required and not (attribute.value_id or attribute.value_name)
        )
        if missing:
            raise UserError(
                "Completá los atributos requeridos: %s"
                % ", ".join(missing.mapped("attribute_name"))
            )
        attributes = self.attribute_line_ids.to_payload()
        if "SELLER_SKU" not in {attribute.get("id") for attribute in attributes}:
            attributes.append({"id": "SELLER_SKU", "value_name": self.sku.strip()})
        if self.barcode and "GTIN" not in {attribute.get("id") for attribute in attributes}:
            attributes.append({"id": "GTIN", "value_name": self.barcode})
        if self.brand:
            attributes.append({"id": "BRAND", "value_name": self.brand})
        if self.model_name:
            attributes.append({"id": "MODEL", "value_name": self.model_name})
        required_result = provider.get_category_required_fields(self.category_id)
        required = required_result.get("items") if isinstance(required_result, dict) else []
        provided_ids = {attribute.get("id") for attribute in attributes}
        missing_ids = [
            attribute.get("name") or attribute.get("id")
            for attribute in required or []
            if isinstance(attribute, dict)
            and attribute.get("id")
            and attribute.get("id") not in provided_ids
        ]
        if missing_ids:
            raise UserError(
                "Cargá y completá los atributos requeridos: %s" % ", ".join(missing_ids)
            )

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
            "seller_custom_field": self.sku.strip(),
            "seller_sku": self.sku.strip(),
            "family_name": self.family_name or self.title,
            "provider_data": {
                "remote_product_id": self.remote_product_id,
                "family_name": self.family_name or self.title,
            },
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


class RemotePublicationAttributeLine(models.TransientModel):
    _name = "marketplace.remote.publication.attribute.line"
    _description = "Atributo temporal de publicación remota"
    _order = "required desc, attribute_name"

    publication_line_id = fields.Many2one(
        "marketplace.remote.publication.wizard.line", required=True, ondelete="cascade"
    )
    attribute_id = fields.Char(string="ID atributo ML", required=True, readonly=True)
    attribute_name = fields.Char(string="Atributo", required=True, readonly=True)
    required = fields.Boolean(string="Requerido", readonly=True)
    value_type = fields.Char(string="Tipo", readonly=True)
    value_name = fields.Char(string="Valor")
    value_id = fields.Char(string="ID valor")
    allowed_values_json = fields.Text(string="Opciones permitidas", readonly=True)

    def action_show_options(self):
        self.ensure_one()
        try:
            options = json.loads(self.allowed_values_json or "[]")
        except (TypeError, ValueError):
            options = []
        if not options:
            message = "Mercado Libre permite ingresar un valor libre para este atributo."
        else:
            lines = [f"Opciones para {self.attribute_name}:"]
            for option in options[:20]:
                if not isinstance(option, dict):
                    continue
                name = option.get("name") or "Sin nombre"
                option_id = option.get("id") or "Sin ID"
                lines.append(f"• {name} — ID: {option_id}")
            if len(options) > 20:
                lines.append(f"… y {len(options) - 20} opciones más.")
            lines.append("Ingresá el nombre o ID en el atributo.")
            message = "\n".join(lines)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Opciones de Mercado Libre",
                "message": Markup(
                    "<pre style='margin:0; white-space:pre-wrap; font-family:inherit;'>%s</pre>"
                    % message
                ),
                "type": "info",
                "sticky": True,
            },
        }

    def to_payload(self):
        payload = []
        for line in self:
            if not line.value_id and not line.value_name:
                continue
            value = {"id": line.attribute_id}
            if line.value_id:
                value["value_id"] = line.value_id
            if line.value_name:
                value["value_name"] = line.value_name
            payload.append(value)
        return payload
