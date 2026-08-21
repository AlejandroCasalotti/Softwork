# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models
from odoo.exceptions import UserError


class MarketplacePublication(models.Model):
    _name = "marketplace.publication"
    _description = "Publicación de un producto en un marketplace"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # Relación
    product_tmpl_id = fields.Many2one(
        "product.template", string="Producto", required=True, ondelete="cascade", index=True
    )
    account_id = fields.Many2one(
        "sce.account", string="Cuenta", required=True, index=True, ondelete="restrict"
    )
    connector_id = fields.Many2one(
        "sce.connector", string="Conector", related="account_id.connector_id", store=True, readonly=True
    )
    provider_type = fields.Selection(
        string="Tipo de proveedor", related="connector_id.provider_type", store=True, readonly=True
    )

    # Identidad externa
    external_id = fields.Char(string="ID externo")
    external_url = fields.Char(string="URL publicación")
    external_status = fields.Char(string="Estado en marketplace", readonly=True)

    # Estado del flujo interno de publicación (no confundir con external_status)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("category", "Categoría"),
            ("attributes", "Atributos"),
            ("pricing", "Precio y stock"),
            ("shipping", "Entrega"),
            ("pictures", "Imágenes"),
            ("ready", "Listo para publicar"),
            ("publishing", "Publicando"),
            ("published", "Publicado"),
            ("failed", "Error"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    error_message = fields.Text(string="Último error")

    # Datos comerciales genéricos
    title = fields.Char(string="Título")
    category_ref = fields.Char(string="Categoría (código externo)")
    category_name = fields.Char(string="Categoría (nombre)")
    listing_type = fields.Char(string="Tipo de publicación")
    condition = fields.Selection(
        [("new", "Nuevo"), ("used", "Usado"), ("not_specified", "No especificado")],
        string="Condición",
        default="new",
    )
    shipping_mode = fields.Char(string="Modo de envío")

    price = fields.Float(string="Precio publicado")
    price_uom_id = fields.Many2one("uom.uom", string="UoM de precio")
    pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    use_pricelist_price = fields.Boolean(string="Usar precio de lista", default=True)
    manual_price_override = fields.Boolean(string="Usar precio manual", default=False)
    stock_reserve_qty = fields.Float(string="Stock reservado", default=0.0)
    effective_qty = fields.Integer(
        string="Stock a publicar", compute="_compute_effective_qty", store=True
    )

    attributes_json = fields.Text(string="Atributos JSON", default="[]")
    pictures_json = fields.Text(string="Imágenes JSON", default="[]")
    sale_terms_json = fields.Text(string="Sale terms JSON", default="[]")
    provider_data_json = fields.Text(string="Datos específicos del proveedor", default="{}")

    published_date = fields.Datetime(string="Fecha de publicación", readonly=True)
    sync_date = fields.Datetime(string="Última sincronización", readonly=True)

    _uniq_product_account = models.Constraint(
        "UNIQUE(product_tmpl_id, account_id)",
        "Ya existe una publicación de este producto para esta cuenta.",
    )

    @api.depends("product_tmpl_id.qty_available", "stock_reserve_qty")
    def _compute_effective_qty(self):
        for publication in self:
            reserve = max(0.0, publication.stock_reserve_qty or 0.0)
            available = publication.product_tmpl_id.qty_available if publication.product_tmpl_id else 0.0
            publication.effective_qty = int(max(0.0, available - reserve))

    def name_get(self):
        result = []
        for publication in self:
            label = publication.title or publication.product_tmpl_id.display_name
            account_name = publication.account_id.display_name
            result.append((publication.id, f"{label} [{account_name}]"))
        return result

    def _validate_for_operation(self):
        self.ensure_one()
        missing = []
        if not self.product_tmpl_id:
            missing.append("producto")
        if not self.account_id:
            missing.append("cuenta")
        if not self.category_ref:
            missing.append("categoría")
        if not self.title:
            missing.append("título")
        if self.price <= 0:
            missing.append("precio")
        for field_name, expected_type in (
            ("attributes_json", list),
            ("pictures_json", list),
            ("sale_terms_json", list),
            ("provider_data_json", dict),
        ):
            raw_value = getattr(self, field_name) or ("{}" if expected_type is dict else "[]")
            try:
                parsed_value = json.loads(raw_value)
            except (TypeError, ValueError) as err:
                raise UserError(
                    "Los datos de '%s' no son JSON válido: %s" % (field_name, err)
                ) from err
            if not isinstance(parsed_value, expected_type):
                raise UserError("Los datos de '%s' tienen un formato inválido." % field_name)
        pictures = json.loads(self.pictures_json or "[]")
        invalid_picture = next(
            (
                picture
                for picture in pictures
                if not isinstance(picture, dict)
                or not str(picture.get("source") or "").strip().startswith(("http://", "https://"))
            ),
            None,
        )
        if invalid_picture:
            missing.append("imágenes públicas válidas")
        if missing:
            raise UserError("La publicación no está lista. Completa: %s." % ", ".join(missing))

    def _apply_provider_result(self, result, published=False):
        self.ensure_one()
        result = result if isinstance(result, dict) else {}
        values = {"sync_date": fields.Datetime.now(), "error_message": False}
        external_id = result.get("item_id") or result.get("external_id")
        if external_id:
            values["external_id"] = str(external_id)
        if result.get("url") or result.get("external_url"):
            values["external_url"] = result.get("url") or result.get("external_url")
        if result.get("status"):
            values["external_status"] = result["status"]
        if published:
            values.update({"state": "published", "published_date": fields.Datetime.now()})
        self.write(values)
        if external_id:
            mapping_model = self.env["marketplace.product.mapping"]
            mapping = mapping_model.search(
                [("publication_id", "=", self.id), ("external_id", "=", str(external_id))],
                limit=1,
            )
            mapping_values = {
                "publication_id": self.id,
                "product_tmpl_id": self.product_tmpl_id.id,
                "product_id": self.product_tmpl_id.product_variant_id.id
                if len(self.product_tmpl_id.product_variant_ids) == 1
                else False,
                "external_id": str(external_id),
            }
            if mapping:
                mapping.write(mapping_values)
            else:
                mapping_model.create(mapping_values)

    def _publication_service(self):
        return self.env["marketplace.publication.service"]

    def action_publish(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "publish")
        return True

    def action_update_marketplace(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "update")
        return True

    def action_sync_marketplace_stock(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "update_stock")
        return True

    def action_sync_marketplace_price(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "update_price")
        return True

    def action_sync_from_marketplace(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "sync")
        return True

    def action_delete_marketplace(self):
        for publication in self:
            publication._publication_service().enqueue(publication, "delete")
        return True
