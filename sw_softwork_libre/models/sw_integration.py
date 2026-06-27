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
    meli_auth_code = fields.Char(string="Código de autorización ML")
    meli_access_token = fields.Char(string="Access Token ML")
    meli_user_id = fields.Char(string="ML User ID")
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

    def _ensure_meli_account(self):
        self.ensure_one()
        if self.integration_type_id != "meli":
            raise UserError("Esta acción solo está disponible para integraciones MercadoLibre.")
        if self.meli_account_id:
            return self.meli_account_id

        account = self.env["sw.ml.account"].create({
            "name": f"{self.name} - MercadoLibre",
            "active": True,
            "site_id": "MLA",
            "client_id": "",
            "client_secret": "",
            "redirect_uri": "",
        })
        self.meli_account_id = account.id
        return account

    def _validate_meli_ready(self):
        self.ensure_one()
        account = self._ensure_meli_account()
        if not account.access_token and not self.meli_access_token:
            raise UserError("No hay Access Token. Debes autorizar e intercambiar código primero.")

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
        self.ensure_one()
        account = self._ensure_meli_account()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sw.ml.account",
            "res_id": account.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_meli_authorize(self):
        self.ensure_one()
        account = self._ensure_meli_account()
        if not (account.client_id and account.redirect_uri):
            raise UserError("Primero completá Client ID y Redirect URI en la cuenta MercadoLibre.")
        return {
            "type": "ir.actions.act_url",
            "url": account.oauth_url,
            "target": "new",
        }

    def action_meli_exchange_code(self):
        self.ensure_one()
        account = self._ensure_meli_account()
        if not self.meli_auth_code:
            raise UserError("Debes pegar el código de autorización de MercadoLibre.")
        account.auth_code = self.meli_auth_code
        account.action_exchange_code()
        self.meli_access_token = account.access_token
        self.meli_user_id = account.seller_id
        return True

    def test_and_confirm(self):
        self.ensure_one()
        account = self._ensure_meli_account()
        if not account.access_token:
            raise UserError("No hay Access Token. Ejecutá primero el intercambio de código.")
        me = account._ml_request("GET", "/users/me")
        self.meli_user_id = str(me.get("id") or "")
        self.meli_access_token = account.access_token
        self.state = "confirmed"
        return True

    def action_meli_clear_data(self):
        self.ensure_one()
        account = self._ensure_meli_account()
        account.write({
            "auth_code": False,
            "access_token": False,
            "refresh_token": False,
            "token_type": False,
            "token_expires_at": False,
            "seller_id": False,
        })
        self.write({
            "meli_auth_code": False,
            "meli_access_token": False,
            "meli_user_id": False,
            "state": "draft",
        })
        return True

    def action_edit_odoo_account(self):
        return True

    def action_add_odoo_account(self):
        return True