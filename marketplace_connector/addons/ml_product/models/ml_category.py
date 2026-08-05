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

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    category_id = fields.Char(required=True, index=True)
    category_name = fields.Char(required=True, index=True)

    _sql_constraints = [
        ("ml_category_unique", "unique(account_id, category_id)", "La categoría ML ya existe para esta cuenta."),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = rec.category_name or rec.category_id
            result.append((rec.id, label))
        return result

    @api.model
    def refresh_for_account(self, account, query=""):
        if not account:
            raise UserError("Cuenta ML inválida para refrescar categorías.")
        provider = ProviderFactory.get_provider(account)
        items = []
        try:
            if hasattr(provider, "search_categories"):
                resp = provider.search_categories(query=query or "")
                items = resp.get("items") if isinstance(resp, dict) else []
            elif hasattr(provider, "sync"):
                resp = provider.sync(
                    {"operation": "search_categories", "payload": {"query": query or ""}}
                )
                items = resp.get("items") if isinstance(resp, dict) else []
        except Exception:
            _logger.exception("Error refrescando categorías ML para account_id=%s", account.id)
            items = []

        if not isinstance(items, list):
            items = []

        vals_list = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = (item.get("id") or item.get("category_id") or "").strip()
            cname = (item.get("name") or item.get("category_name") or "").strip()
            if not cid:
                continue
            vals_list.append(
                {
                    "account_id": account.id,
                    "category_id": cid,
                    "category_name": cname or cid,
                }
            )

        existing = self.search([("account_id", "=", account.id)])
        existing_map = {rec.category_id: rec for rec in existing}

        seen = set()
        for vals in vals_list:
            cid = vals["category_id"]
            seen.add(cid)
            rec = existing_map.get(cid)
            if rec:
                rec.write({"category_name": vals["category_name"]})
            else:
                self.create(vals)

        if seen:
            (existing - self.search([("account_id", "=", account.id), ("category_id", "in", list(seen))])).unlink()

        return True