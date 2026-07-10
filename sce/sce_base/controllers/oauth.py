# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

OAuth Controller
"""


from odoo import http


from odoo.http import request



class SCEOAuthController(http.Controller):


    @http.route(
        "/sce/oauth/callback",
        type="http",
        auth="public",
        csrf=False,
    )
    def oauth_callback(
        self,
        code=None,
        state=None,
        **kwargs,
    ):

        if not code:

            return request.make_response(

                "Missing authorization code",

                headers=[
                    (
                        "Content-Type",
                        "text/plain",
                    )
                ],

            )


        account_id = False


        if state:

            try:

                account_id = int(
                    state
                )

            except Exception:

                account_id = False



        if not account_id:

            return request.make_response(

                "Invalid OAuth state",

                headers=[
                    (
                        "Content-Type",
                        "text/plain",
                    )
                ],

            )



        account = request.env[
            "sce.account"
        ].sudo().browse(
            account_id
        )



        if not account.exists():

            return request.make_response(

                "Account not found",

                headers=[
                    (
                        "Content-Type",
                        "text/plain",
                    )
                ],

            )



        request.env[
            "sce.oauth.service"
        ].sudo().exchange_code(

            account,

            code,

        )



        return request.make_response(

            "OAuth connection completed",

            headers=[
                (
                    "Content-Type",
                    "text/plain",
                )
            ],

        )