# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ml_publish_enabled = fields.Boolean(string="Publicar en MercadoLibre", default=False)
    ml_account_id = fields.Many2one("ml.account", string="Cuenta ML")

    ml_title = fields.Char(string="Título ML")
    ml_subtitle = fields.Char(string="Subtítulo ML")
    ml_category_id = fields.Char(string="Categoría ML")
    ml_listing_type = fields.Char(string="Tipo de publicación", default="gold_special")
    ml_condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
        default="new",
    )
    ml_brand = fields.Char(string="Marca")
    ml_model = fields.Char(string="Modelo")
    ml_warranty = fields.Char(string="Garantía")
    ml_price = fields.Float(string="Precio ML")
    ml_quantity = fields.Float(string="Cantidad ML")
    ml_video = fields.Char(string="Video")
    ml_description_html = fields.Html(string="Descripción HTML")
    ml_attributes_json = fields.Text(string="Atributos JSON")

    ml_status = fields.Char(string="Estado ML", readonly=True)
    ml_permalink = fields.Char(string="URL publicación", readonly=True)
    ml_item_id = fields.Char(string="ID Publicación", readonly=True)
    ml_publish_date = fields.Datetime(string="Fecha publicación", readonly=True)
    ml_sync_date = fields.Datetime(string="Última sincronización", readonly=True)

    def _get_ml_account(self):
        self.ensure_one()
        account = self.ml_account_id or self.env["ml.account"].search([("active", "=", True)], limit=1)
        if not account:
            raise UserError("No hay una cuenta MercadoLibre activa configurada.")
        return account

    def _effective_title(self):
        self.ensure_one()
        return (self.ml_title or self.name or "").strip()

    def _effective_price(self):
        self.ensure_one()
        return self.ml_price if self.ml_price > 0 else self.list_price

    def _effective_qty(self):
        self.ensure_one()
        qty = self.ml_quantity if self.ml_quantity > 0 else self.qty_available
        return int(max(0, qty))

    def _build_ml_payload(self):
        self.ensure_one()
        title = self._effective_title()
        if not title:
            raise UserError("Falta título para publicar en MercadoLibre.")
        price = self._effective_price()
        if price <= 0:
            raise UserError("El precio debe ser mayor a cero.")
        qty = self._effective_qty()

        category = self.ml_category_id or "MLA3530"
        listing_type = self.ml_listing_type or "gold_special"

        payload = {
            "title": title,
            "category_id": category,
            "price": price,
            "currency_id": "ARS",
            "available_quantity": qty,
            "buying_mode": "buy_it_now",
            "condition": self.ml_condition or "new",
            "listing_type_id": listing_type,
            "sale_terms": [],
            "pictures": [],
            "attributes": [],
        }

        if self.ml_warranty:
            payload["sale_terms"].append({"id": "WARRANTY_TYPE", "value_name": self.ml_warranty})

        if self.ml_brand:
            payload["attributes"].append({"id": "BRAND", "value_name": self.ml_brand})
        if self.ml_model:
            payload["attributes"].append({"id": "MODEL", "value_name": self.ml_model})

        if self.ml_description_html:
            payload["description"] = {"plain_text": self.ml_description_html}

        if self.image_1920:
            payload["pictures"].append({"source": "data:image/jpeg;base64,%s" % self.image_1920.decode()})

        return payload

    def action_publish_ml(self):
        for product in self:
            if not product.ml_publish_enabled:
                continue
            account = product._get_ml_account()
            payload = product._build_ml_payload()

            if product.ml_item_id:
                response = account.ml_request("PUT", f"/items/{product.ml_item_id}", payload=payload)
            else:
                response = account.ml_request("POST", "/items", payload=payload)

            product.write({
                "ml_item_id": response.get("id") or product.ml_item_id,
                "ml_status": response.get("status") or product.ml_status,
                "ml_permalink": response.get("permalink") or product.ml_permalink,
                "ml_publish_date": fields.Datetime.now() if not product.ml_publish_date else product.ml_publish_date,
                "ml_sync_date": fields.Datetime.now(),
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "MercadoLibre",
                "message": "Producto publicado/actualizado correctamente.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_update_ml(self):
        return self.action_publish_ml()

    def action_pause_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            account.ml_request("PUT", f"/items/{product.ml_item_id}", payload={"status": "paused"})
            product.write({"ml_status": "paused", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_reactivate_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            account.ml_request("PUT", f"/items/{product.ml_item_id}", payload={"status": "active"})
            product.write({"ml_status": "active", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_close_ml(self):
        for product in self:
            if not product.ml_item_id:
                continue
            account = product._get_ml_account()
            account.ml_request("PUT", f"/items/{product.ml_item_id}", payload={"status": "closed"})
            product.write({"ml_status": "closed", "ml_sync_date": fields.Datetime.now()})
        return True

    def action_view_ml(self):
        self.ensure_one()
        if not self.ml_permalink:
            raise UserError("Este producto no tiene URL de publicación.")
        return {
            "type": "ir.actions.act_url",
            "url": self.ml_permalink,
            "target": "new",
        }