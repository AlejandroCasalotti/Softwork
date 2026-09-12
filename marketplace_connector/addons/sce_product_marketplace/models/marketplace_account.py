# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class MarketplaceAccount(models.Model):
    _inherit = "sce.account"

    # --- 1. Vinculación Producto - Publicación & Multicompañía ---
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
    odoo_company_name = fields.Char(
        string="Compañía Odoo",
        help="Nombre o ID de la compañía en Odoo (para opción multicompañía).",
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
        string="Almacén de Stock",
        help="Nombre, código o ID de la ubicación/almacén físico en Odoo del cual consultar el stock.",
    )

    # --- 3. Sincronización de Precios & Recargos ---
    pricelist_name = fields.Char(
        string="Lista de Precios Odoo",
        help="Nombre o ID de la lista de precios predeterminada en Odoo.",
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
        help="Nombre o ID del equipo de ventas a asignar en Odoo (Si se deja vacío, se creará/usará el equipo 'Mercado Libre').",
    )
    warehouse_name = fields.Char(
        string="Almacén Odoo Estándar",
        help="Nombre o ID del almacén para órdenes normales de Mercado Libre.",
    )
    fulfillment_warehouse_name = fields.Char(
        string="Almacén Odoo Fulfillment",
        help="Nombre o ID del almacén para ventas FULL de Mercado Libre.",
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

    # --- 6. Métodos RPC para mapear opciones desde el Odoo del cliente ---
    def _get_remote_odoo_rpc(self):
        self.ensure_one()
        url = (self.odoo_base_url or "").strip().rstrip('/')
        db = (self.odoo_db_name or "").strip()
        user = (self.odoo_user or "").strip()
        password = (self.odoo_password or "").strip()

        if not url or not db or not user or not password:
            raise UserError(
                "Para mapear opciones, primero debes completar la URL, Base de datos, Usuario y Clave API de Odoo en la sección 'Conexión con Odoo'."
            )

        try:
            import xmlrpc.client
            common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
            uid = common.authenticate(db, user, password, {})
            if not uid:
                raise UserError("Autenticación fallida con el Odoo remoto. Verificá tu usuario y contraseña/API Key.")
            models_rpc = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
            return db, uid, password, models_rpc
        except UserError:
            raise
        except Exception as err:
            raise UserError(f"No se pudo conectar con el Odoo remoto: {err}") from err

    def _fetch_remote_odoo_records(self, model_name, domain=None, fields_to_read=None):
        db, uid, password, models_rpc = self._get_remote_odoo_rpc()
        domain = domain or []
        fields_to_read = fields_to_read or ["id", "name"]
        try:
            records = models_rpc.execute_kw(
                db, uid, password,
                model_name, "search_read",
                [domain],
                {"fields": fields_to_read, "limit": 25}
            )
            return records or []
        except Exception as err:
            raise UserError(f"Error al consultar '{model_name}' en Odoo remoto: {err}")

    def _notify_odoo_options(self, title, records, code_field=None, note=None):
        if not records:
            msg = f"No se encontraron registros en tu Odoo para {title}."
            if note:
                msg += f"\n\n💡 Nota: {note}"
        else:
            items = []
            for rec in records:
                rec_id = rec.get("id")
                name = rec.get("name") or rec.get("display_name") or "Sin nombre"
                code = f" [{rec.get(code_field)}]" if code_field and rec.get(code_field) else ""
                items.append(f"• ID {rec_id} : {name}{code}")
            msg = f"📋 Opciones de {title} en tu Odoo:\n\n" + "\n".join(items)
            if note:
                msg += f"\n\n💡 Nota: {note}"
            msg += "\n\nIngresá el nombre o el número de ID directamente en el campo."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": f"Mapeo Odoo: {title}",
                "message": msg,
                "type": "info",
                "sticky": True,
            },
        }

    def action_fetch_odoo_companies(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records("res.company")
        return self._notify_odoo_options("Compañías Odoo", records)

    def action_fetch_odoo_stock_locations(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records(
            "stock.warehouse",
            fields_to_read=["id", "name", "code"]
        )
        if not records:
            records = self._fetch_remote_odoo_records(
                "stock.location",
                domain=[("usage", "=", "internal")],
                fields_to_read=["id", "complete_name", "name"]
            )
            for rec in records:
                if rec.get("complete_name"):
                    rec["name"] = rec["complete_name"]
        return self._notify_odoo_options("Almacenes de Stock", records, code_field="code")

    def action_fetch_odoo_pricelists(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records("product.pricelist")
        return self._notify_odoo_options("Listas de Precios", records)

    def action_fetch_odoo_sales_teams(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records("crm.team")
        note = "Si no completás este campo, se creará o asignará automáticamente el equipo 'Mercado Libre' en tu Odoo."
        return self._notify_odoo_options("Equipos de Ventas", records, note=note)

    def action_fetch_odoo_warehouses(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records("stock.warehouse", fields_to_read=["id", "name", "code"])
        return self._notify_odoo_options("Almacenes Estándar", records, code_field="code")

    def action_fetch_odoo_fulfillment_warehouses(self):
        self.ensure_one()
        records = self._fetch_remote_odoo_records("stock.warehouse", fields_to_read=["id", "name", "code"])
        note = "Seleccioná o ingresá el ID/nombre del almacén Odoo asignado para ventas FULL (Fulfillment)."
        return self._notify_odoo_options("Almacenes Fulfillment", records, code_field="code", note=note)

    # --- 7. Test de Conciliación y Estado de Productos ---
    def action_check_products_status(self):
        self.ensure_one()
        total_ml = 0
        if self.provider_type == "mercadolibre":
            try:
                provider = self.env["sce.provider.factory"].get_provider(self)
                user_id = self.external_user_id
                if not user_id:
                    me = provider._request("GET", "/users/me", with_auth=True)
                    user_id = me.get("id") if isinstance(me, dict) else False
                    if user_id:
                        self.sudo().write({"external_user_id": str(user_id)})
                if user_id:
                    res = provider._request("GET", f"/users/{user_id}/items/search", with_auth=True, params={"limit": 1})
                    total_ml = res.get("paging", {}).get("total", 0) if isinstance(res, dict) else 0
            except Exception:
                total_ml = 0

        pub_model = self.env["marketplace.publication"]
        total_sce = pub_model.search_count([("account_id", "=", self.id)])
        reconciled = pub_model.search_count([
            ("account_id", "=", self.id),
            ("external_id", "!=", False),
            ("product_tmpl_id", "!=", False),
        ])
        unreconciled_ml = max(0, total_ml - reconciled)

        if total_ml > 0:
            rate = round((reconciled / float(total_ml)) * 100.0, 1)
        elif total_sce > 0:
            rate = 100.0 if reconciled == total_sce else round((reconciled / float(total_sce)) * 100.0, 1)
        else:
            rate = 0.0

        if rate >= 100.0 and total_ml > 0:
            status_state = "full"
            summary_msg = f"Se encontraron {total_ml} publicaciones en Mercado Libre y las {reconciled} están totalmente conciliadas y vinculadas con productos en Odoo."
            rec_notes = "Todo está sincronizado correctamente. No se requieren acciones adicionales."
        elif reconciled > 0:
            status_state = "partial"
            summary_msg = f"De un total de {total_ml} publicaciones en Mercado Libre, {reconciled} están vinculadas con Odoo y {unreconciled_ml} se encuentran pendientes de conciliar."
            rec_notes = "Te recomendamos ejecutar la sincronización para importar y vincular los productos faltantes de Mercado Libre."
        else:
            status_state = "none"
            summary_msg = f"Mercado Libre reporta {total_ml} publicaciones en tu cuenta, pero ninguna está asociada a productos de Odoo todavía."
            rec_notes = "Haz clic en 'Sincronizar Faltantes desde Mercado Libre' para vincular tus publicaciones automáticamente."

        wizard = self.env["marketplace.product.status.wizard"].create({
            "account_id": self.id,
            "total_ml_items": total_ml,
            "total_sce_publications": total_sce,
            "reconciled_count": reconciled,
            "unreconciled_ml_count": unreconciled_ml,
            "reconciliation_rate": min(100.0, rate),
            "status_state": status_state,
            "summary_message": summary_msg,
            "recommendation_notes": rec_notes,
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Estados de productos y conciliación",
            "res_model": "marketplace.product.status.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }