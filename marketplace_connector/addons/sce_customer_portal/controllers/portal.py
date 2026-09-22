# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class SceCustomerPortal(CustomerPortal):
    @http.route("/my/sce", type="http", auth="user", website=True)
    def portal_sce_dashboard(self, **kwargs):
        partner = request.env.user.partner_id.commercial_partner_id
        subscription = request.env["sce.subscription"].sudo().get_or_create_portal_subscription(partner)
        account = request.env["sce.account"].sudo().search(
            [("company_id", "=", subscription.company_id.id), ("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            order="create_date desc",
            limit=1,
        ) if subscription else request.env["sce.account"]
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "subscription": subscription,
                "account": account,
                "summaries": subscription.usage_summary_ids[:6] if subscription else request.env["sce.usage.summary"],
                "page_name": "sce_subscription",
            }
        )
        return request.render("sce_customer_portal.portal_sce_dashboard", values)

    @http.route("/my/sce/odoo", type="http", auth="user", website=True, methods=["POST"])
    def portal_save_odoo_connection(self, **post):
        partner = request.env.user.partner_id.commercial_partner_id
        subscription = request.env["sce.subscription"].sudo().search(
            [("partner_id", "=", partner.id), ("state", "!=", "cancelled")], limit=1
        )
        if not subscription:
            return request.redirect("/my/sce")
        account = request.env["sce.account"].sudo().search(
            [("company_id", "=", subscription.company_id.id), ("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            order="create_date desc",
            limit=1,
        )
        if account:
            account.write(
                {
                    "odoo_base_url": (post.get("odoo_base_url") or "").strip(),
                    "odoo_db_name": (post.get("odoo_db_name") or "").strip(),
                    "odoo_user": (post.get("odoo_user") or "").strip(),
                    "odoo_password": post.get("odoo_password") or "",
                    "sync_stock": post.get("sync_stock") == "on",
                    "sync_prices": post.get("sync_prices") == "on",
                    "sync_orders": post.get("sync_orders") == "on",
                }
            )
            try:
                account._get_remote_odoo_rpc()
                request.session["sce_portal_notice"] = "Conexión Odoo validada. La sincronización inicial quedó encolada si Mercado Libre ya está conectado."
            except Exception as error:
                request.session["sce_portal_error"] = str(error)
        return request.redirect("/my/sce")

    @http.route("/my/sce/connect/mercadolibre", type="http", auth="user", website=True)
    def portal_connect_mercadolibre(self, **kwargs):
        return request.redirect("/sce/oauth/mercadolibre/start")
