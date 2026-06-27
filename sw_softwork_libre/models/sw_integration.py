# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SwIntegration(models.Model):
    _name = "sw.integration"
    _description = "Integración Ecommerce"

    name = fields.Char(string="Nombre", required=True, default="Nueva Integración")
    state = fields.Selection(
        [("draft", "Borrador"), ("confirmed", "Confirmada")],
        string="Estado",
        default="draft",
        required=True,
    )

    integration_type_id = fields.Selection(
        [
            ("odoo", "Odoo"),
            ("meli", "MercadoLibre"),
            ("shopify", "Shopify"),
            ("tiendanube", "Tiendanube"),
        ],
        string="Tipo de Integración",
        required=True,
    )
    country_id = fields.Many2one("res.country", string="País")

    is_odoo_odoo = fields.Boolean(compute="_compute_type_flags", store=False)
    is_odoo_meli = fields.Boolean(compute="_compute_type_flags", store=False)
    is_odoo_shopify = fields.Boolean(compute="_compute_type_flags", store=False)
    is_odoo_tiendanube = fields.Boolean(compute="_compute_type_flags", store=False)

    ecommerce_account_set = fields.Boolean(compute="_compute_ecommerce_account_set", store=False)

    shopify_account_id = fields.Char(string="Cuenta Shopify")
    tiendanube_account_id = fields.Char(string="Cuenta Tiendanube")
    meli_account_id = fields.Many2one("sw.ml.account", string="Cuenta MercadoLibre")
    odoo_account_id = fields.Char(string="Cuenta Odoo")

    odoo_stock_location_id = fields.Many2one("stock.location", string="Ubicación de Stock Odoo")

    odoo_match_field = fields.Selection(
        [
            ("default_code", "Referencia Interna (default_code)"),
            ("barcode", "Código de Barras (barcode)"),
            ("id", "ID de Odoo"),
        ],
        string="Campo de Vinculación",
        default="default_code",
    )
    exclude_products_domain = fields.Char(string="Dominio Exclusión Productos")

    sync_orders = fields.Boolean(string="Sincronizar Ventas")
    sync_stock = fields.Boolean(string="Sincronizar Stock")
    sync_prices = fields.Boolean(string="Sincronizar Precios")
    sync_full_sales = fields.Boolean(string="Sincronización Completa Ventas")
    sync_only_paid_orders = fields.Boolean(string="Solo Órdenes Pagas")

    last_sync = fields.Datetime(string="Última Sync")
    last_sync_start = fields.Datetime(string="Inicio Última Sync")
    last_cron_execution = fields.Datetime(string="Última Ejecución Cron")
    cron_nextcall = fields.Datetime(string="Próxima Ejecución Cron")

    @api.depends("integration_type_id")
    def _compute_type_flags(self):
        for rec in self:
            rec.is_odoo_odoo = rec.integration_type_id == "odoo"
            rec.is_odoo_meli = rec.integration_type_id == "meli"
            rec.is_odoo_shopify = rec.integration_type_id == "shopify"
            rec.is_odoo_tiendanube = rec.integration_type_id == "tiendanube"

    @api.depends("shopify_account_id", "tiendanube_account_id", "meli_account_id", "odoo_account_id")
    def _compute_ecommerce_account_set(self):
        for rec in self:
            rec.ecommerce_account_set = bool(
                rec.shopify_account_id
                or rec.tiendanube_account_id
                or rec.meli_account_id
                or rec.odoo_account_id
            )

    def _validate_meli_ready(self):
        self.ensure_one()
        if self.integration_type_id != "meli":
            raise UserError("Esta acción solo está disponible para integraciones MercadoLibre.")
        if not self.meli_account_id:
            raise UserError("Debes configurar una Cuenta MercadoLibre en la integración.")
        if not self.meli_account_id.access_token:
            raise UserError("La Cuenta MercadoLibre no tiene Access Token. Autorizá la cuenta primero.")

    def _touch_sync_start(self):
        self.write({"last_sync_start": fields.Datetime.now()})

    def _touch_sync_end(self):
        self.write({
            "last_sync": fields.Datetime.now(),
            "last_cron_execution": fields.Datetime.now(),
        })

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"
        return True

    def action_set_draft(self):
        for rec in self:
            rec.state = "draft"
        return True

    def action_sync_orders(self):
        for rec in self:
            rec._validate_meli_ready()
            rec._touch_sync_start()
            metrics = rec.env["sale.order"].action_ml_import_orders(
                account=rec.meli_account_id,
                integration=rec,
            )
            rec._touch_sync_end()
            _logger.info("Integración %s - sync orders: %s", rec.display_name, metrics)
        return True

    def action_sync_stock(self):
        for rec in self:
            rec._validate_meli_ready()
            rec._touch_sync_start()
            metrics = rec.env["product.template"].action_ml_sync_price_stock(
                account=rec.meli_account_id,
                integration=rec,
                mode="stock",
            )
            rec._touch_sync_end()
            _logger.info("Integración %s - sync stock: %s", rec.display_name, metrics)
        return True

    def action_sync_prices(self):
        for rec in self:
            rec._validate_meli_ready()
            rec._touch_sync_start()
            metrics = rec.env["product.template"].action_ml_sync_price_stock(
                account=rec.meli_account_id,
                integration=rec,
                mode="price",
            )
            rec._touch_sync_end()
            _logger.info("Integración %s - sync prices: %s", rec.display_name, metrics)
        return True

    @api.model
    def cron_run_integrations(self):
        integrations = self.search([("state", "=", "confirmed"), ("integration_type_id", "=", "meli")])
        for integ in integrations:
            try:
                if integ.sync_prices:
                    integ.action_sync_prices()
                if integ.sync_stock:
                    integ.action_sync_stock()
                if integ.sync_orders:
                    integ.action_sync_orders()
            except Exception as err:
                _logger.exception("Error ejecutando integración %s: %s", integ.display_name, err)

    def action_edit_shopify_account(self):
        return True

    def action_shopify_authorize(self):
        return True

    def action_edit_tiendanube_account(self):
        return True

    def action_tiendanube_authorize(self):
        return True

    def action_edit_meli_account(self):
        return True

    def action_meli_authorize(self):
        for rec in self:
            rec._validate_meli_ready()
            return {
                "type": "ir.actions.act_url",
                "url": rec.meli_account_id.oauth_url,
                "target": "new",
            }
        return True

    def action_edit_odoo_account(self):
        return True

    def action_add_odoo_account(self):
        return True