# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class SceMlTestSaleWizard(models.TransientModel):
    _name = "sce.ml.test.sale.wizard"
    _description = "Prueba de venta completa Mercado Libre"

    account_id = fields.Many2one(
        "sce.account",
        string="Cuenta vendedora de prueba",
        required=True,
        domain="[('provider_type', '=', 'mercadolibre'), ('mode', '=', 'sandbox'), ('state', '=', 'connected')]",
    )
    publication_id = fields.Many2one(
        "marketplace.publication",
        string="Publicación de prueba",
        required=True,
        domain="[('account_id', '=', account_id), ('state', '=', 'published'), ('external_id', '!=', False)]",
    )
    site_id = fields.Char(string="Sitio", default="MLA", required=True)
    state = fields.Selection(
        [
            ("setup", "Preparar prueba"),
            ("waiting_order", "Esperando compra de prueba"),
            ("done", "Orden importada en borrador"),
        ],
        default="setup",
        required=True,
    )
    buyer_external_id = fields.Char(readonly=True)
    buyer_nickname = fields.Char(readonly=True)
    buyer_email = fields.Char(readonly=True)
    buyer_password = fields.Char(readonly=True)
    purchase_url = fields.Char(readonly=True)
    external_order_id = fields.Char(readonly=True)
    remote_sale_order_name = fields.Char(readonly=True)
    result_message = fields.Text(readonly=True)

    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get("default_account_id"):
            values["account_id"] = self.env.context["default_account_id"]
        return values

    def _validate_seller(self):
        self.ensure_one()
        account = self.account_id
        if account.provider_type != "mercadolibre" or account.mode != "sandbox":
            raise UserError("Esta prueba solo está disponible para una cuenta Mercado Libre de prueba.")
        if account.state != "connected" or not account.access_token:
            raise UserError("Conectá la cuenta vendedora de prueba antes de iniciar.")
        if not account.odoo_base_url or not account.odoo_db_name or not account.odoo_user or not account.odoo_password:
            raise UserError("Configurá primero la conexión Odoo asociada a esta cuenta.")
        if not self.publication_id or self.publication_id.account_id != account:
            raise UserError("Elegí una publicación vinculada a esta cuenta de prueba.")
        if (
            self.publication_id.state != "published"
            or not self.publication_id.external_id
            or not self.publication_id.external_url
        ):
            raise UserError("La publicación debe estar publicada y tener URL e ID externos.")
        return account

    def action_prepare_test_sale(self):
        self.ensure_one()
        account = self._validate_seller()
        account._get_remote_odoo_rpc()
        provider = self.env["sce.provider.factory"].get_provider(account)
        seller = provider._request("GET", "/users/me")
        tags = seller.get("tags", []) if isinstance(seller, dict) else []
        seller_id = str(
            (seller.get("id") if isinstance(seller, dict) else False)
            or account.external_user_id
            or ""
        )
        if not seller_id or not isinstance(tags, list) or "test_user" not in tags:
            raise UserError(
                "Mercado Libre no identificó esta cuenta como usuario de prueba. "
                "No se creará una compra para evitar operaciones en producción."
            )

        buyer = provider.create_test_user(
            site_id=(self.site_id or "MLA").strip().upper(),
            description="SCE test buyer",
        )
        if str(buyer.get("id") or "") == seller_id:
            raise UserError(
                "Mercado Libre devolvió el mismo usuario para vendedor y comprador. "
                "La prueba se detuvo para evitar una compra inválida."
            )
        self.write(
            {
                "buyer_external_id": str(buyer["id"]),
                "buyer_nickname": buyer.get("nickname") or "",
                "buyer_email": buyer.get("email") or "",
                "buyer_password": buyer.get("password") or "",
                "purchase_url": self.publication_id.external_url,
                "state": "waiting_order",
                "result_message": (
                    "Comprador de prueba creado. Iniciá sesión en Mercado Libre con estas "
                    "credenciales, completá la compra de la publicación y luego presioná "
                    "“Verificar e importar orden”. La importación se fuerza a borrador."
                ),
            }
        )
        return self._reload_action()

    def action_open_purchase_page(self):
        self.ensure_one()
        if self.state != "waiting_order" or not self.purchase_url:
            raise UserError("Primero prepará la compra de prueba.")
        return {
            "type": "ir.actions.act_url",
            "url": self.purchase_url,
            "target": "new",
        }

    @staticmethod
    def _find_matching_order(orders, buyer_id, item_id):
        buyer_id = str(buyer_id or "")
        item_id = str(item_id or "")
        for order in orders:
            if not isinstance(order, dict):
                continue
            buyer = order.get("buyer")
            if not isinstance(buyer, dict) or str(buyer.get("id") or "") != buyer_id:
                continue
            for line in order.get("order_items") or []:
                item = line.get("item") if isinstance(line, dict) else False
                if isinstance(item, dict) and str(item.get("id") or "") == item_id:
                    return order
        return False

    def action_check_and_import_order(self):
        self.ensure_one()
        if self.state != "waiting_order" or not self.buyer_external_id:
            raise UserError("Prepará primero la compra con un usuario comprador de prueba.")
        account = self._validate_seller()
        provider = self.env["sce.provider.factory"].get_provider(account)
        matches = []
        for page in range(5):
            response = provider.get_orders({"offset": page * 50, "limit": 50})
            orders = response.get("items", []) if isinstance(response, dict) else []
            match = self._find_matching_order(
                orders,
                self.buyer_external_id,
                self.publication_id.external_id,
            )
            if match:
                matches.append(match)
                break
            if len(orders) < 50:
                break
        if not matches:
            raise UserError(
                "Todavía no encontramos una orden de este comprador para la publicación elegida. "
                "Completá el checkout con el usuario de prueba y volvé a verificar."
            )

        order = matches[0]
        external_order_id = str(order.get("id") or "")
        if not external_order_id:
            raise UserError("Mercado Libre devolvió una orden sin ID.")
        result = self.env["marketplace.publication.service"].import_order(
            account, external_order_id, force_draft=True
        )
        self.write(
            {
                "state": "done",
                "external_order_id": external_order_id,
                "remote_sale_order_name": result.get("sale_order_name") or "",
                "result_message": (
                    "La orden de prueba fue enviada al Odoo configurado como presupuesto "
                    "(borrador). No se confirmó ni se facturó."
                ),
                "buyer_password": False,
            }
        )
        return self._reload_action()

    def _reload_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Prueba de venta Mercado Libre",
            "res_model": self._name,
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
            "target": "new",
        }

    def action_close_wizard(self):
        self.write({"buyer_password": False})
        return {"type": "ir.actions.act_window_close"}
