# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


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
        try:
            action = account.action_open_oauth_url()
            return request.redirect(action.get("url"))
        except Exception as err:
            msg = str(err) or "No se pudo iniciar la conexión OAuth."
            if "configuración interna de la aplicación Mercado Libre" in msg:
                return request.redirect("/sce/oauth/mercadolibre/result?status=missing_config")
            return request.redirect("/sce/oauth/mercadolibre/result?status=error")

    @http.route(
        ["/sce/oauth/mercadolibre/callback"],
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def sce_ml_oauth_callback(self, **kwargs):
        state = kwargs.get("state")
        code = kwargs.get("code") or kwargs.get("authorization_code")
        error = kwargs.get("error")
        _logger.info(
            "ML OAuth callback received: state=%s has_code=%s code_len=%s keys=%s",
            state,
            bool(code),
            len((code or "").strip()),
            sorted(list(kwargs.keys())),
        )

        if not state:
            return request.redirect("/web#action=base.action_res_users")

        transaction = request.env["sce.oauth.transaction"].sudo().search(
            [("state_hash", "=", request.env["sce.oauth.transaction"].hash_state(state))],
            limit=1,
        )
        account = transaction.account_id if transaction else False

        if error:
            if account:
                account.write(
                    {
                        "state": "error",
                        "last_error": "Mercado Libre no pudo autorizar la conexión. Reintentá nuevamente.",
                    }
                )
            return request.redirect("/sce/oauth/mercadolibre/result?status=error")

        if code:
            try:
                clean_code = (code or "").strip()
                from odoo.addons.sce_connector_ml.services.mercadolibre_oauth_service import MercadoLibreOAuthService

                MercadoLibreOAuthService(request.env).complete(state, clean_code, request.env.user)
            except Exception as err:
                err_msg = str(err)
                if account:
                    if "invalid_grant" in err_msg or "volver a autorizar la conexión" in err_msg:
                        try:
                            from odoo.addons.sce_connector_ml.services.mercadolibre_token_service import (
                                MercadoLibreTokenService,
                            )

                            MercadoLibreTokenService(request.env).mark_auth_required(account)
                        except Exception:
                            _logger.exception(
                                "No se pudieron limpiar los tokens ML luego de invalid_grant para account_id=%s",
                                account.id,
                            )
                        account.write(
                            {
                                "state": "error",
                                "token_expires_at": False,
                                "last_error": "Mercado Libre necesita que vuelvas a autorizar la conexión.",
                            }
                        )
                        return request.redirect("/sce/oauth/mercadolibre/result?status=reauthorize")
                    account.write({"state": "error", "last_error": err_msg})
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
            <p>Tu cuenta de Mercado Libre ya quedó conectada y lista para sincronizar productos, precios, stock y ventas.</p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        elif status == "missing_config":
            html = """
            <html><body style="font-family: Arial, sans-serif; padding: 24px;">
            <h2>⚙️ Falta la configuración interna de Mercado Libre</h2>
            <p>La conexión comercial está lista, pero un administrador todavía debe completar la configuración técnica de la aplicación una sola vez.</p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        elif status == "reauthorize":
            html = """
            <html><body style="font-family: Arial, sans-serif; padding: 24px;">
            <h2>🔁 Mercado Libre necesita autorización</h2>
            <p>La autorización anterior ya no es válida. Para continuar, autorizá nuevamente la conexión.</p>
            <p><a href="/sce/oauth/mercadolibre/start">Reintentar conexión ahora</a></p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        else:
            html = """
            <html><body style="font-family: Arial, sans-serif; padding: 24px;">
            <h2>⚠️ No se pudo completar la conexión</h2>
            <p>Reintentá la conexión desde Odoo. Si el problema continúa, revisá la configuración interna de Mercado Libre desde administración.</p>
            <p><a href="/web">Volver a Odoo</a></p>
            </body></html>
            """
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])