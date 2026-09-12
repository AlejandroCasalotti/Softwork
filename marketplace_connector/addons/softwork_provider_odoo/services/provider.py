# -*- coding: utf-8 -*-
import json
import logging
import xmlrpc.client

from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_interface import IProvider

_logger = logging.getLogger(__name__)


class OdooProvider(IProvider):
    """
    Provider externo base para conectores tipo 'odoo'.
    Soporta validación de credenciales y health check para Odoo→Odoo.
    """

    def __init__(self, env, account):
        self.env = env
        self.account = account

    def capabilities(self):
        return {
            "oauth_exchange": False,
            "oauth_refresh": False,
            "health_check": True,
        }

    def _odoo_target(self):
        if getattr(self.account, "odoo_source_url", False):
            return {
                "url": self.account.odoo_source_url,
                "db": self.account.odoo_source_db,
                "user": self.account.odoo_source_user,
                "password": self.account.odoo_source_api_key,
            }
        if getattr(self.account, "odoo_base_url", False):
            return {
                "url": self.account.odoo_base_url,
                "db": self.account.odoo_db_name,
                "user": self.account.odoo_user,
                "password": self.account.odoo_password,
            }
        raise UserError(
            "No hay configuración Odoo disponible para este proveedor. "
            "Completa URL, base de datos, usuario y password/API key."
        )

    def _connect(self):
        params = self._odoo_target()
        clean_url = (params["url"] or "").strip()
        db = (params["db"] or "").strip()
        user = (params["user"] or "").strip()
        password = (params["password"] or "").strip()

        if not clean_url:
            raise UserError("Falta URL de Odoo en la cuenta.")
        if not db:
            raise UserError("Falta base de datos de Odoo en la cuenta.")
        if not user:
            raise UserError("Falta usuario de Odoo en la cuenta.")
        if not password:
            raise UserError("Falta password/API key de Odoo en la cuenta.")

        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        common = xmlrpc.client.ServerProxy(f"{clean_url.rstrip('/')}/xmlrpc/2/common")
        uid = common.authenticate(db, user, password, {})
        if not uid:
            raise UserError("Credenciales Odoo inválidas o sin acceso a la base de datos.")

        models_rpc = xmlrpc.client.ServerProxy(f"{clean_url.rstrip('/')}/xmlrpc/2/object")
        return uid, db, user, password, models_rpc

    def authenticate(self):
        uid, db, user, password, _ = self._connect()
        return {
            "ok": True,
            "provider": "odoo",
            "action": "authenticate",
            "uid": uid,
            "db": db,
            "user": user,
            "password": "***",
            "account_id": getattr(self.account, "id", None),
            "connector_id": getattr(getattr(self.account, "connector_id", None), "id", None),
        }

    def refresh_token(self):
        raise UserError("El provider Odoo no usa OAuth ni refresh token; usa usuario/API key.")

    def health(self):
        uid, db, user, _, _ = self._connect()
        return {
            "ok": True,
            "provider": "odoo",
            "account_id": getattr(self.account, "id", None),
            "connector_id": getattr(getattr(self.account, "connector_id", None), "id", None),
            "uid": uid,
            "db": db,
            "user": user,
        }

    def publish_product(self, payload):
        raise UserError("La sincronización de marketplace no está implementada para el provider Odoo.")

    def update_product(self, payload):
        raise UserError("La actualización de productos no está implementada para el provider Odoo.")

    def delete_product(self, payload):
        raise UserError("El borrado de productos no está implementado para el provider Odoo.")

    def update_stock(self, payload):
        raise UserError("La actualización de stock no está implementada para el provider Odoo.")

    def update_price(self, payload):
        raise UserError("La actualización de precios no está implementada para el provider Odoo.")

    def get_item(self, external_id):
        raise UserError("El provider Odoo no expone un catálogo marketplace por item.")

    def get_orders(self, params=None):
        raise UserError("El provider Odoo no expone un endpoint de pedidos marketplace.")

    def get_order(self, external_id):
        raise UserError("El provider Odoo no expone una consulta de pedido marketplace.")

    def cancel_order(self, external_id):
        raise UserError("El provider Odoo no expone cancelación de pedidos marketplace.")

    def get_messages(self, params=None):
        raise UserError("El provider Odoo no expone mensajería marketplace.")

    def answer_message(self, payload):
        raise UserError("El provider Odoo no expone respuesta de mensajes marketplace.")

    def download_invoice(self, external_id):
        raise UserError("El provider Odoo no expone descarga de factura marketplace.")

    def upload_invoice(self, payload):
        raise UserError("El provider Odoo no expone subida de factura marketplace.")

    def search_categories(self, query, limit=20):
        query = (query or "").strip()
        if not query:
            return {"ok": True, "provider": "odoo", "items": [], "raw": []}

        uid, db, _, password, models_rpc = self._connect()
        domain = [("name", "ilike", query)]
        ids = models_rpc.execute_kw(db, uid, password, "product.public.category", "search", [domain], {"limit": int(limit or 20), "offset": 0})
        records = models_rpc.execute_kw(
            db,
            uid,
            password,
            "product.public.category",
            "read",
            [ids],
            ["id", "name", "parent_id"],
        )
        return {
            "ok": True,
            "provider": "odoo",
            "query": query,
            "items": [
                {
                    "category_id": str(item.get("id") or ""),
                    "category_name": item.get("name") or "",
                    "parent_id": item.get("parent_id") or False,
                }
                for item in records or []
            ],
            "raw": records or [],
        }

    def get_category_attributes(self, category_id):
        return {
            "ok": True,
            "provider": "odoo",
            "category_id": category_id,
            "items": [],
            "raw": [],
        }

    def get_category_required_fields(self, category_id):
        return {
            "ok": True,
            "provider": "odoo",
            "category_id": category_id,
            "items": [],
            "total_required": 0,
            "raw": [],
        }

    def get_listing_prices(self, category_id, price, listing_type_id):
        return {
            "ok": True,
            "provider": "odoo",
            "category_id": category_id,
            "listing_type_id": listing_type_id,
            "items": [],
            "raw": [],
        }

    def sync(self, params=None):
        return {
            "ok": True,
            "provider": "odoo",
            "action": "sync",
            "params": params or {},
        }

    def webhook(self, payload):
        return {
            "ok": True,
            "provider": "odoo",
            "payload": payload or {},
        }


def get_provider(env, account):
    """
    Factory requerida por convención:
    <modulo>.services.provider.get_provider
    """
    _logger.info(
        "Resolviendo provider externo Odoo para cuenta %s (connector %s)",
        getattr(account, "id", None),
        getattr(getattr(account, "connector_id", None), "id", None),
    )
    provider = OdooProvider(env, account)
    return provider