# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Main Controllers
"""


from odoo import http


from odoo.http import request



class SCEController(http.Controller):
    """
    Base SCE HTTP Controller.
    """



    @http.route(
        "/sce",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def index(self):

        return {

            "name":
                "Softwork Commerce Engine",

            "status":
                "running",

            "version":
                "19.0",

        }



    @http.route(
        "/sce/info",
        type="json",
        auth="public",
        csrf=False,
    )
    def info(self):

        return {

            "module":
                "sce_base",

            "odoo_version":
                request.env[
                    "ir.module.module"
                ].search(
                    [
                        (
                            "name",
                            "=",
                            "sce_base",
                        )
                    ],
                    limit=1,
                ).installed_version,

        }