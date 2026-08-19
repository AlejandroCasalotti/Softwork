# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

_logger = logging.getLogger(__name__)


class MlAttributeEditorWizard(models.TransientModel):
    _name = "ml.attribute.editor.wizard"
    _description = "Editor dinámico de atributos MercadoLibre"

    product_tmpl_id = fields.Many2one("product.template", required=True, readonly=True)
    publication_id = fields.Many2one(
        "marketplace.publication", string="Publicación", readonly=True, ondelete="cascade"
    )
    account_id = fields.Many2one(
        "sce.account",
        string="Cuenta ML",
        domain="[('provider_type', '=', 'mercadolibre')]",
        required=True,
    )
    category_id = fields.Char(string="Categoría ML", required=True, readonly=True)
    attribute_id = fields.Char(string="ID atributo")
    attribute_name = fields.Char(string="Atributo")
    option_id = fields.Many2one(
        "ml.attribute.option",
        string="Opción",
        domain="[('category_id', '=', category_id), ('attribute_id', '=', attribute_id)]",
    )
    value_name = fields.Char(string="Valor")
    value_id = fields.Char(string="ID valor")
    has_options = fields.Boolean(string="Tiene opciones", default=False)
    is_required = fields.Boolean(string="Requerido", default=True)
    line_ids = fields.One2many(
        "ml.attribute.editor.wizard.line",
        "wizard_id",
        string="Atributos",
    )

    def _raise_if_access_denied_response(self, payload, operation):
        if isinstance(payload, str):
            text = payload.lower()
            if "<html" in text and "access denied" in text:
                _logger.error(
                    "Access Denied detectado en operación ML '%s' para account_id=%s",
                    operation,
                    self.account_id.id if self.account_id else False,
                )
                raise UserError(
                    "Acceso denegado por el servicio remoto. "
                    "Revisa permisos/sesión de Odoo.sh y credenciales de la cuenta ML."
                )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        product_id = self.env.context.get("default_product_tmpl_id")
        if not product_id:
            return vals

        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            return vals

        account = product.ml_account_id or self.env["sce.account"].search(
            [("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            limit=1,
        )
        if not account:
            raise UserError("No hay una cuenta SCE MercadoLibre activa configurada.")
        publication = self.env["marketplace.publication"].browse(
            self.env.context.get("default_publication_id")
        ).exists()
        if not publication:
            publication = self.env["marketplace.publication"].search(
                [("product_tmpl_id", "=", product.id), ("account_id", "=", account.id)],
                limit=1,
            )
        category_id = (publication.category_ref if publication else product.ml_category_id or "").strip()
        if not category_id:
            raise UserError("Primero debes definir una categoría ML para cargar atributos requeridos.")

        vals.update(
            {
                "product_tmpl_id": product.id,
                "publication_id": publication.id if publication else False,
                "account_id": account.id,
                "category_id": category_id,
            }
        )
        return vals

    def action_load_required(self):
        self.ensure_one()
        provider = ProviderFactory.get_provider(self.account_id)
        req_res = provider.get_category_required_fields(category_id=self.category_id)
        self._raise_if_access_denied_response(req_res, "get_category_required_fields")
        required = req_res.get("items") if isinstance(req_res, dict) else []
        if not isinstance(required, list):
            _logger.warning(
                "Respuesta inesperada en get_category_required_fields account_id=%s category_id=%s: %s",
                self.account_id.id,
                self.category_id,
                type(req_res).__name__,
            )
            required = []
        required_ids = {(a.get("id") or "").strip() for a in required if isinstance(a, dict)}
        required_ids.discard("")

        attrs_res = provider.get_category_attributes(category_id=self.category_id)
        self._raise_if_access_denied_response(attrs_res, "get_category_attributes")
        all_attrs = attrs_res.get("items") if isinstance(attrs_res, dict) else []
        if not isinstance(all_attrs, list):
            _logger.warning(
                "Respuesta inesperada en get_category_attributes account_id=%s category_id=%s: %s",
                self.account_id.id,
                self.category_id,
                type(attrs_res).__name__,
            )
            all_attrs = []

        current_attrs = []
        raw = self.publication_id.attributes_json if self.publication_id else self.product_tmpl_id.ml_attributes_json
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    current_attrs = [a for a in parsed if isinstance(a, dict)]
            except Exception:
                _logger.exception(
                    "Error parseando atributos en editor para product_tmpl_id=%s",
                    self.product_tmpl_id.id,
                )
                current_attrs = []
        current_map = {(a.get("id") or "").strip(): a for a in current_attrs if (a.get("id") or "").strip()}

        self.line_ids.unlink()
        commands = []
        for attr in all_attrs:
            if not isinstance(attr, dict):
                continue
            attr_id = (attr.get("id") or "").strip()
            if not attr_id:
                continue
            existing = current_map.get(attr_id, {})
            value_name = existing.get("value_name") or ""
            value_id = existing.get("value_id") or ""

            values = attr.get("values") if isinstance(attr.get("values"), list) else []
            has_options = bool(values)

            option_id = False
            if has_options:
                for val in values:
                    if not isinstance(val, dict):
                        continue
                    value_id_candidate = (val.get("id") or "").strip()
                    value_name_candidate = (val.get("name") or "").strip() or (val.get("value_name") or "").strip()
                    option_model = self.env["ml.attribute.option"].sudo()
                    option_domain = [
                        ("category_id", "=", self.category_id),
                        ("attribute_id", "=", attr_id),
                        ("value_id", "=", value_id_candidate),
                        ("value_name", "=", value_name_candidate),
                    ]
                    existing_opt = option_model.search(option_domain, limit=1)
                    if not existing_opt:
                        try:
                            option_model.create(
                                {
                                    "account_id": self.account_id.id,
                                    "category_id": self.category_id,
                                    "attribute_id": attr_id,
                                    "attribute_name": attr.get("name") or attr_id,
                                    "value_id": value_id_candidate,
                                    "value_name": value_name_candidate,
                                }
                            )
                        except Exception:
                            _logger.warning(
                                "Posible concurrencia/duplicado creando ml.attribute.option "
                                "account_id=%s category_id=%s attribute_id=%s value_id=%s",
                                self.account_id.id,
                                self.category_id,
                                attr_id,
                                value_id_candidate,
                            )
                            existing_opt = option_model.search(option_domain, limit=1)
                            if not existing_opt:
                                raise
                if value_id:
                    option = self.env["ml.attribute.option"].search(
                        [
                            ("category_id", "=", self.category_id),
                            ("attribute_id", "=", attr_id),
                            ("value_id", "=", value_id),
                        ],
                        limit=1,
                    )
                    option_id = option.id if option else False

            commands.append(
                (
                    0,
                    0,
                    {
                        "attribute_id": attr_id,
                        "attribute_name": attr.get("name") or attr_id,
                        "option_id": option_id,
                        "value_name": value_name,
                        "value_id": value_id,
                        "has_options": has_options,
                        "is_required": attr_id in required_ids,
                    },
                )
            )
        if commands:
            self.write({"line_ids": commands})
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.attribute.editor.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_save(self):
        self.ensure_one()
        attrs = []
        for line in self.line_ids:
            attr_id = (line.attribute_id or "").strip()
            if not attr_id:
                continue
            item = {"id": attr_id}
            if line.value_id:
                item["value_id"] = line.value_id
            if line.value_name:
                item["value_name"] = (line.value_name or "").strip()
            attrs.append(item)

        attributes_json = json.dumps(attrs, ensure_ascii=False)
        provider_data = {}
        if self.publication_id.provider_data_json:
            try:
                provider_data = json.loads(self.publication_id.provider_data_json)
            except (TypeError, ValueError):
                provider_data = {}
        for item in attrs:
            if item["id"] == "BRAND" and item.get("value_name"):
                provider_data["brand"] = item.get("value_name")
            if item["id"] == "MODEL" and item.get("value_name"):
                provider_data["model"] = item.get("value_name")
        if self.publication_id:
            self.publication_id.write(
                {
                    "attributes_json": attributes_json,
                    "provider_data_json": json.dumps(provider_data, ensure_ascii=False),
                    "state": "attributes",
                }
            )
        vals = {"ml_attributes_json": attributes_json}
        if provider_data.get("brand"):
            vals["ml_brand"] = provider_data["brand"]
        if provider_data.get("model"):
            vals["ml_model"] = provider_data["model"]
        self.product_tmpl_id.write(vals)
        return {"type": "ir.actions.act_window_close"}


class MlAttributeEditorWizardLine(models.TransientModel):
    _name = "ml.attribute.editor.wizard.line"
    _description = "Línea de atributo requerido MercadoLibre"

    wizard_id = fields.Many2one("ml.attribute.editor.wizard", required=True, ondelete="cascade")
    category_id = fields.Char(related="wizard_id.category_id", store=False, readonly=True)
    attribute_id = fields.Char(string="ID atributo", required=True, readonly=True)
    attribute_name = fields.Char(string="Atributo", required=True, readonly=True)
    option_id = fields.Many2one(
        "ml.attribute.option",
        string="Opción",
        domain="[('category_id', '=', category_id), ('attribute_id', '=', attribute_id)]",
    )
    value_name = fields.Char(string="Valor")
    value_id = fields.Char(string="ID valor", readonly=True)
    has_options = fields.Boolean(string="Tiene opciones", default=False, readonly=True)
    is_required = fields.Boolean(string="Requerido", default=True, readonly=True)

    @api.onchange("option_id")
    def _onchange_option_id(self):
        for line in self:
            if line.option_id:
                line.value_id = line.option_id.value_id or ""
                line.value_name = line.option_id.value_name or ""