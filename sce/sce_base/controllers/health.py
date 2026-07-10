# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Health Controller
"""


from odoo import http



class SCEHealthController(http.Controller):



    @http.route(
        "/sce/health",
        type="json",
        auth="public",
        csrf=False,
    )
    def health(self):

        return {

            "status":
                "ok",

            "service":
                "sce",

        }



    @http.route(
        "/sce/ping",
        type="json",
        auth="public",
        csrf=False,
    )
    def ping(self):

        return {

            "pong":
                True

        }