# -*- coding: utf-8 -*-
import csv
import io

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class SceCustomerPortal(CustomerPortal):
    def _get_portal_subscription(self, create=False):
        partner = request.env.user.partner_id.commercial_partner_id
        if create:
            return request.env["sce.subscription"].sudo().get_or_create_portal_subscription(partner)
        return request.env["sce.subscription"].sudo().search(
            [("partner_id", "=", partner.id), ("state", "!=", "cancelled")],
            order="create_date desc",
            limit=1,
        )

    def _get_portal_account(self, subscription):
        if not subscription:
            return request.env["sce.account"]
        return request.env["sce.account"].sudo().search(
            [("company_id", "=", subscription.company_id.id), ("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            order="create_date desc",
            limit=1,
        )

    def _get_portal_ml_accounts(self, subscription):
        if not subscription:
            return request.env["sce.account"]
        return request.env["sce.account"].sudo().search(
            [("company_id", "=", subscription.company_id.id), ("provider_type", "=", "mercadolibre"), ("active", "=", True)],
            order="create_date desc",
        )

    def _get_portal_account_by_id(self, subscription, account_id):
        if not subscription or not account_id:
            return self._get_portal_account(subscription)
        return request.env["sce.account"].sudo().search(
            [
                ("id", "=", int(account_id)),
                ("company_id", "=", subscription.company_id.id),
                ("provider_type", "=", "mercadolibre"),
                ("active", "=", True),
            ],
            limit=1,
        )

    @http.route("/my/sce", type="http", auth="user", website=True)
    def portal_sce_dashboard(self, **kwargs):
        subscription = self._get_portal_subscription(create=True)
        account = self._get_portal_account(subscription)
        ml_accounts = self._get_portal_ml_accounts(subscription)
        total_products = request.env["marketplace.publication"].sudo().search_count(
            [("account_id", "in", ml_accounts.ids), ("state", "=", "published")]
        ) if ml_accounts else 0
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "subscription": subscription,
                "account": account,
                "ml_accounts": ml_accounts,
                "total_products": total_products,
                "summaries": subscription.usage_summary_ids[:6] if subscription else request.env["sce.usage.summary"],
                "page_name": "sce_subscription",
                "notice": request.session.pop("sce_portal_notice", None),
                "error": request.session.pop("sce_portal_error", None),
            }
        )
        return request.render("sce_customer_portal.portal_sce_dashboard", values)

    @http.route("/my/sce/odoo", type="http", auth="user", website=True, methods=["POST"])
    def portal_save_odoo_connection(self, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account(subscription)
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
                for ml_account in self._get_portal_ml_accounts(subscription).filtered(lambda a: a.state == "connected"):
                    ml_account._enqueue_initial_sync_if_ready()
                request.session["sce_portal_notice"] = "Conexión Odoo validada. La sincronización inicial quedó encolada si Mercado Libre ya está conectado."
            except Exception as error:
                request.session["sce_portal_error"] = str(error)
        return request.redirect("/my/sce")

    @http.route("/my/sce/account/<int:account_id>/sync/<string:operation>", type="http", auth="user", website=True, methods=["POST"])
    def portal_account_sync_control(self, account_id, operation, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, account_id)
        if account:
            if operation == "start":
                account.action_start_initial_sync()
                request.session["sce_portal_notice"] = "Sincronización inicial encolada."
            elif operation == "pause":
                account.action_pause_sync()
                request.session["sce_portal_notice"] = "Sincronización pausada para esta cuenta."
            elif operation == "resume":
                account.action_resume_sync()
                request.session["sce_portal_notice"] = "Sincronización reanudada para esta cuenta."
        return request.redirect("/my/sce")

    @http.route("/my/sce/connect/mercadolibre", type="http", auth="user", website=True)
    def portal_connect_mercadolibre(self, **kwargs):
        subscription = self._get_portal_subscription(create=True)
        account = request.env["sce.account"].sudo().create_quick_ml_account(company=subscription.company_id)
        if not account.installment_rule_ids:
            account._seed_default_installment_rules()
        return request.redirect(f"/sce/oauth/mercadolibre/start?account_id={account.id}")

    @http.route(["/my/sce/rules", "/my/sce/rules/<int:account_id>"], type="http", auth="user", website=True)
    def portal_sce_rules(self, account_id=None, **kwargs):
        subscription = self._get_portal_subscription(create=True)
        account = self._get_portal_account_by_id(subscription, account_id)
        if account and not account.installment_rule_ids:
            account._seed_default_installment_rules()
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "subscription": subscription,
                "account": account,
                "installment_rules": account.installment_rule_ids if account else request.env["marketplace.installment.rule"],
                "stock_reserve_rules": account.stock_reserve_rule_ids if account else request.env["marketplace.stock.reserve.rule"],
                "page_name": "sce_rules",
                "notice": request.session.pop("sce_portal_notice", None),
            }
        )
        return request.render("sce_customer_portal.portal_sce_rules", values)

    @http.route("/my/sce/rules/save", type="http", auth="user", website=True, methods=["POST"])
    def portal_save_rules(self, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, post.get("account_id"))
        if account:

            def _to_float(value, default=0.0):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default

            def _to_int(value, default=0):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return default

            account.write(
                {
                    "safety_stock": _to_int(post.get("safety_stock")),
                    "sync_stock_flex": post.get("sync_stock_flex") == "on",
                    "price_security_factor": _to_float(post.get("price_security_factor")),
                    "price_surcharge_fixed": _to_float(post.get("price_surcharge_fixed")),
                    "price_surcharge_percent": _to_float(post.get("price_surcharge_percent")),
                    "free_shipping_threshold": _to_float(post.get("free_shipping_threshold")),
                    "free_shipping_fee": _to_float(post.get("free_shipping_fee")),
                    "stock_location_name": (post.get("stock_location_name") or "").strip(),
                    "pricelist_name": (post.get("pricelist_name") or "").strip(),
                    "odoo_company_name": (post.get("odoo_company_name") or "").strip(),
                    "sales_team_name": (post.get("sales_team_name") or "").strip(),
                    "warehouse_name": (post.get("warehouse_name") or "").strip(),
                    "fulfillment_warehouse_name": (post.get("fulfillment_warehouse_name") or "").strip(),
                    "sync_orders_full": post.get("sync_orders_full") == "on",
                    "marketplace_auto_confirm_paid": post.get("marketplace_auto_confirm_paid") == "on",
                    "marketplace_auto_cancelled": post.get("marketplace_auto_cancelled") == "on",
                    "sync_ml_questions": post.get("sync_ml_questions") == "on",
                    "ml_question_retention_days": max(1, _to_int(post.get("ml_question_retention_days"), 30)),
                }
            )
            for rule in account.installment_rule_ids:
                value = post.get(f"surcharge_{rule.id}")
                if value is not None:
                    rule.sudo().write({"surcharge_percent": _to_float(value)})
            request.session["sce_portal_notice"] = "Reglas de stock y precios actualizadas."
        return request.redirect(f"/my/sce/rules/{account.id}" if account else "/my/sce/rules")

    @http.route("/my/sce/rules/stock-reserve/add", type="http", auth="user", website=True, methods=["POST"])
    def portal_add_stock_reserve_rule(self, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, post.get("account_id"))
        if account:
            sku = (post.get("sku") or "").strip()
            reserve_qty = int(post.get("reserve_qty") or 0)
            if sku:
                rule = request.env["marketplace.stock.reserve.rule"].sudo().search(
                    [("account_id", "=", account.id), ("sku", "=", sku)], limit=1
                )
                values = {"account_id": account.id, "sku": sku, "reserve_qty": max(0, reserve_qty), "active": True}
                if rule:
                    rule.write(values)
                else:
                    request.env["marketplace.stock.reserve.rule"].sudo().create(values)
                request.session["sce_portal_notice"] = "Reserva por SKU guardada."
        return request.redirect(f"/my/sce/rules/{account.id}" if account else "/my/sce/rules")

    @http.route("/my/sce/rules/stock-reserve/delete/<int:rule_id>", type="http", auth="user", website=True, methods=["POST"])
    def portal_delete_stock_reserve_rule(self, rule_id, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, post.get("account_id"))
        if account:
            rule = request.env["marketplace.stock.reserve.rule"].sudo().search(
                [("id", "=", rule_id), ("account_id", "=", account.id)], limit=1
            )
            rule.unlink()
            request.session["sce_portal_notice"] = "Reserva por SKU eliminada."
        return request.redirect(f"/my/sce/rules/{account.id}" if account else "/my/sce/rules")

    @http.route("/my/sce/rules/stock-reserve/import", type="http", auth="user", website=True, methods=["POST"])
    def portal_import_stock_reserve_rules(self, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, post.get("account_id"))
        upload = request.httprequest.files.get("reserve_file")
        imported = 0
        if account and upload:
            content = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                sku = (row.get("sku") or row.get("default_code") or "").strip()
                if not sku:
                    continue
                try:
                    reserve_qty = max(0, int(float(row.get("reserve_qty") or 0)))
                except (TypeError, ValueError):
                    continue
                rule = request.env["marketplace.stock.reserve.rule"].sudo().search(
                    [("account_id", "=", account.id), ("sku", "=", sku)], limit=1
                )
                values = {"account_id": account.id, "sku": sku, "reserve_qty": reserve_qty, "active": True}
                if rule:
                    rule.write(values)
                else:
                    request.env["marketplace.stock.reserve.rule"].sudo().create(values)
                imported += 1
            request.session["sce_portal_notice"] = f"Reservas importadas: {imported}."
        return request.redirect(f"/my/sce/rules/{account.id}" if account else "/my/sce/rules")

    @http.route("/my/sce/remote-options", type="jsonrpc", auth="user", methods=["POST"])
    def portal_remote_options(self, option_type=None, **kwargs):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, kwargs.get("account_id"))
        if not account:
            return {"ok": False, "error": "Primero conectá tu cuenta de Mercado Libre."}
        options = {
            "companies": ("res.company", [], ["id", "name"], None),
            "stock_locations": ("stock.warehouse", [], ["id", "name", "code"], "code"),
            "pricelists": ("product.pricelist", [], ["id", "name"], None),
            "sales_teams": ("crm.team", [], ["id", "name"], None),
            "warehouses": ("stock.warehouse", [], ["id", "name", "code"], "code"),
        }
        config = options.get(option_type)
        if not config:
            return {"ok": False, "error": "Tipo de opción no permitido."}
        model_name, domain, fields_to_read, code_field = config
        try:
            records = account._fetch_remote_odoo_records(model_name, domain, fields_to_read)
            return {
                "ok": True,
                "items": [
                    {
                        "id": record.get("id"),
                        "name": record.get("name") or record.get("display_name") or "Sin nombre",
                        "code": record.get(code_field) if code_field else False,
                    }
                    for record in records
                ],
            }
        except Exception as error:
            return {"ok": False, "error": str(error)}

    @http.route("/my/sce/rules/installment/restore", type="http", auth="user", website=True, methods=["POST"])
    def portal_restore_installment_rules(self, **post):
        subscription = self._get_portal_subscription()
        account = self._get_portal_account_by_id(subscription, post.get("account_id"))
        if account:
            account.installment_rule_ids.unlink()
            account._seed_default_installment_rules()
            request.session["sce_portal_notice"] = "Reglas sugeridas restauradas."
        return request.redirect(f"/my/sce/rules/{account.id}" if account else "/my/sce/rules")
