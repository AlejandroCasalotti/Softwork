# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SceOAuthController(http.Controller):

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
            return request.redirect(f"/web#id={account.id}&model=sce.account&view_type=form")

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

        return request.redirect(f"/web#id={account.id}&model=sce.account&view_type=form")