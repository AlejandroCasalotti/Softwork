# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

_logger = logging.getLogger(__name__)


class MlCategory(models.Model):
    _name = "ml.category"
    _description = "Categorías MercadoLibre"
    _order = "category_name"
    _rec_name = "category_name"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    category_id = fields.Char(required=True, index=True)
    category_name = fields.Char(required=True, index=True)

    _ml_category_unique = models.Constraint(
        "UNIQUE(account_id, category_id)",
        "La categoría ML ya existe para esta cuenta.",
    )

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.category_name or rec.category_id))
        return result

    @api.model
    def _raise_if_access_denied_response(self, payload, account, operation):
        if isinstance(payload, str) and "<html" in payload.lower() and "access denied" in payload.lower():
            _logger.error(
                "Access Denied detectado en operación ML '%s' para account_id=%s",
                operation,
                account.id if account else False,
            )
            raise UserError(
                "Acceso denegado por el servicio remoto. "
                "Revisa permisos/sesión de Odoo.sh y credenciales de la cuenta ML."
            )

    def refresh_for_account(self, account, query=""):
        if not account:
            raise UserError("Cuenta ML inválida para refrescar categorías.")
        provider = ProviderFactory.get_provider(account)
        items = []
        try:
            if hasattr(provider, "search_categories"):
                response = provider.search_categories(query=query or "")
                self._raise_if_access_denied_response(response, account, "search_categories")
                items = response.get("items") if isinstance(response, dict) else []
            elif hasattr(provider, "sync"):
                response = provider.sync({"operation": "search_categories", "payload": {"query": query or ""}})
                self._raise_if_access_denied_response(response, account, "sync:search_categories")
                items = response.get("items") if isinstance(response, dict) else []
        except Exception:
            _logger.exception("Error refrescando categorías ML para account_id=%s", account.id)
            items = []

        if not isinstance(items, list):
            items = []

        existing = self.search([("account_id", "=", account.id)])
        existing_map = {rec.category_id: rec for rec in existing}
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            category_id = (item.get("id") or item.get("category_id") or "").strip()
            category_name = (item.get("name") or item.get("category_name") or "").strip()
            if not category_id:
                continue
            seen.add(category_id)
            category = existing_map.get(category_id)
            if category:
                category.write({"category_name": category_name or category_id})
            else:
                self.create(
                    {
                        "account_id": account.id,
                        "category_id": category_id,
                        "category_name": category_name or category_id,
                    }
                )
        if seen:
            (existing - self.search([("account_id", "=", account.id), ("category_id", "in", list(seen))])).unlink()