# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
    meli_account_id = fields.Char(string="Cuenta MercadoLibre")
    odoo_account_id = fields.Char(string="Cuenta Odoo")

    odoo_match_field = fields.Selection(
        [
            ("default_code", "Referencia Interna (default_code)"),
            ("barcode", "Código de Barras (barcode)"),
            ("id", "ID de Odoo"),
        ],
        string="Campo de Vinculación",
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

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"
        return True

    def action_set_draft(self):
        for rec in self:
            rec.state = "draft"
        return True

    def _touch_sync(self):
        self.write({"last_sync_start": fields.Datetime.now(), "last_sync": fields.Datetime.now()})

    def action_sync_orders(self):
        self._touch_sync()
        return True

    def action_sync_stock(self):
        self._touch_sync()
        return True

    def action_sync_prices(self):
        self._touch_sync()
        return True

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
        return True

    def action_edit_odoo_account(self):
        return True

    def action_add_odoo_account(self):
        return True