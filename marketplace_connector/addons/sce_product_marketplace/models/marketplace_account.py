# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MarketplaceAccount(models.Model):
    _inherit = "sce.account"

    # --- 1. Vinculación Producto - Publicación ---
    matching_field = fields.Selection(
        selection=[
            ("default", "Referencia Interna / SKU"),
            ("barcode", "Código de Barras"),
        ],
        string="Emparejar Productos por",
        default="default",
        help="Campo de Odoo utilizado para vincular productos con Mercado Libre.",
    )
    exclude_domain = fields.Char(
        string="Filtro de Exclusión de Productos",
        help="Sintaxis de dominio Odoo para ignorar productos en la sincronización, ej: [('type', '=', 'service')]",
    )

    # --- 2. Sincronización de Stock ---
    sync_stock_flex = fields.Boolean(
        string="Sincronizar Stock Flex",
        default=True,
    )
    safety_stock = fields.Integer(
        string="Stock de Seguridad (Unidades a restar)",
        default=0,
        help="Cantidad fija a restar del stock disponible real de Odoo antes de publicar en Mercado Libre.",
    )
    stock_location_name = fields.Char(
        string="Ubicación de Stock Odoo",
        help="Nombre o código de la ubicación física en Odoo de la cual consultar el stock.",
    )

    # --- 3. Sincronización de Precios & Recargos ---
    pricelist_name = fields.Char(
        string="Lista de Precios Odoo",
        help="Nombre de la lista de precios predeterminada en Odoo.",
    )
    price_security_factor = fields.Float(
        string="Factor de Seguridad / Margen (%)",
        default=0.0,
        help="Porcentaje adicional a sumar sobre el precio base de Odoo.",
    )
    price_surcharge_fixed = fields.Float(
        string="Recargo Fijo por Venta ($)",
        default=0.0,
    )
    price_surcharge_percent = fields.Float(
        string="Recargo Porcentual General (%)",
        default=0.0,
    )

    # Recargos por Cuotas / Modalidad de Publicación ML
    surcharge_clasica_percent = fields.Float(
        string="Recargo Publicación Clásica (%)",
        default=0.0,
    )
    surcharge_premium_percent = fields.Float(
        string="Recargo Publicación Premium / Cuotas (%)",
        default=0.0,
        help="Recargo porcentual para publicaciones con cuotas sin interés.",
    )
    free_shipping_threshold = fields.Float(
        string="Precio Umbral Envío Fijo ($)",
        default=33000.0,
        help="Si el precio final es inferior a este monto, se adiciona el cargo fijo de envío de Mercado Libre.",
    )
    free_shipping_fee = fields.Float(
        string="Costo Fijo Envío Precio Bajo ($)",
        default=0.0,
    )

    # --- 4. Sincronización de Ventas y Logística ---
    sync_orders_full = fields.Boolean(
        string="Sincronizar Ventas FULL (Fulfillment)",
        default=True,
    )
    marketplace_auto_confirm_paid = fields.Boolean(
        string="Confirmar órdenes pagadas automáticamente",
        default=True,
    )
    marketplace_auto_cancelled = fields.Boolean(
        string="Cancelar órdenes canceladas automáticamente",
        default=True,
    )
    sales_team_name = fields.Char(
        string="Equipo de Ventas Odoo",
        help="Nombre del equipo de ventas a asignar en Odoo.",
    )
    warehouse_name = fields.Char(
        string="Almacén Odoo Estándar",
        help="Nombre del almacén para órdenes normales de Mercado Libre.",
    )
    fulfillment_warehouse_name = fields.Char(
        string="Almacén Odoo Fulfillment",
        help="Nombre del almacén para ventas FULL de Mercado Libre.",
    )

    # --- 5. Simulador de Precios en Vivo (Live Price Simulator) ---
    sim_base_price = fields.Float(
        string="Precio Base de Prueba ($)",
        default=10000.0,
    )
    sim_calculated_clasica = fields.Float(
        string="Precio Calculado (Clásica)",
        compute="_compute_simulated_prices",
    )
    sim_calculated_premium = fields.Float(
        string="Precio Calculado (Premium / Cuotas)",
        compute="_compute_simulated_prices",
    )

    @api.depends(
        "sim_base_price",
        "price_security_factor",
        "price_surcharge_fixed",
        "price_surcharge_percent",
        "surcharge_clasica_percent",
        "surcharge_premium_percent",
        "free_shipping_threshold",
        "free_shipping_fee",
    )
    def _compute_simulated_prices(self):
        for account in self:
            account.sim_calculated_clasica = account.calculate_marketplace_price(
                account.sim_base_price, listing_type="gold_special"
            )
            account.sim_calculated_premium = account.calculate_marketplace_price(
                account.sim_base_price, listing_type="gold_pro"
            )

    def calculate_marketplace_price(self, base_price, listing_type="gold_special"):
        """Calcula el precio final a publicar en Mercado Libre partiendo del precio base de Odoo
        y aplicando las reglas generales configuradas en la cuenta.
        """
        self.ensure_one()
        base = max(0.0, float(base_price or 0.0))
        if base <= 0:
            return 0.0

        # 1. Aplicar Factor de Seguridad (%)
        subtotal = base * (1.0 + (self.price_security_factor / 100.0))

        # 2. Aplicar Recargo Porcentual General + Recargo Fijo
        subtotal = subtotal * (1.0 + (self.price_surcharge_percent / 100.0)) + self.price_surcharge_fixed

        # 3. Aplicar Recargo por Tipo de Publicación (Clásica vs Premium/Cuotas)
        is_premium = listing_type in ("gold_pro", "premium")
        surcharge_pct = self.surcharge_premium_percent if is_premium else self.surcharge_clasica_percent
        final_price = subtotal * (1.0 + (surcharge_pct / 100.0))

        # 4. Ajuste por Umbral de Envío Gratis / Cargo Fijo
        if self.free_shipping_threshold > 0 and final_price < self.free_shipping_threshold:
            final_price += self.free_shipping_fee

        return round(final_price, 2)

    def calculate_marketplace_stock(self, real_stock):
        """Calcula el stock a enviar a Mercado Libre aplicando el stock de seguridad de la cuenta."""
        self.ensure_one()
        real = max(0, int(real_stock or 0))
        available = real - self.safety_stock
        return max(0, available)