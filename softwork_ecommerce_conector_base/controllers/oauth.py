# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SceOAuthController(http.Controller):

    @http.route(
        ["/sce/oauth/mercadolibre/start"],
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def sce_ml_oauth_start(self, **kwargs):
        company = request.env.company
        account = request.env["sce.account"].sudo().get_or_create_quick_ml_account(company=company)
        action = account.action_open_oauth_url()
        return request.redirect(action.get("url"))

    @http.route(
        ["/sce/oauth/mercadolibre/callback"],
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def sce_ml_oauth_callback(self, **kwargs):
        state = kwargs.get("state")
        code = kwargs.get("code")
        error = kwargs.get("error")

        if not state:
            return request.redirect("/web#action=base.action_res_users")

        try:
            account_id = int(state)
        except Exception:
            return request.redirect("/web#action=base.action_res_users")

        account = request.env["sce.account"].sudo().browse(account_id)
        if not account.exists():
            return request.redirect("/web#action=base.action_res_users")

        if error:
            account.write(
                {
                    "state": "error",
                    "last_error": f"OAuth error: {error}",
                }
            )
            return request.redirect("/sce/oauth/mercadolibre/result?status=error")

        if code:
            try:
                account.write({"auth_code": code})
                account.action_exchange_code()
            except Exception as err:
                account.write(
                    {
                        "state": "error",
                        "last_error": str(err),
                    }
                )
                return request.redirect("/sce/oauth/mercadolibre/result?status=error")

        return request.redirect("/sce/oauth/mercadolibre/result?status=ok")

    @http.route(
        ["/sce/oauth/mercadolibre/result"],
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def sce_ml_oauth_result(self, **kwargs):
        status = kwargs.get("status")
        if status == "ok":
            html = """
            <html><body style="font-family: Arial, sans-serif; padding: 24px;">
            <h2>✅ Cuenta conectada correctamente</h2>
            <p>Tu cuenta de MercadoLibre ya está conectada y sincronizada automáticamente.</p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        else:
            html = """
            <html><body style="font-family: Arial, sans-serif; padding: 24px;">
            <h2>⚠️ No se pudo completar la conexión</h2>
            <p>Reintentá la conexión desde Odoo. Si persiste, revisá la configuración OAuth.</p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])