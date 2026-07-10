# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Webhook Controller
"""


import json


from odoo import http


from odoo.http import request



class SCEWebhookController(http.Controller):



    @http.route(
        "/sce/webhook/<string:connector>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_receiver(
        self,
        connector,
        **kwargs,
    ):


        payload = {}


        try:

            payload = json.loads(

                request.httprequest.data

                or

                "{}"

            )


        except Exception:


            payload = {

                "raw":

                    request.httprequest.data.decode(
                        "utf-8"
                    )

            }



        headers = dict(
            request.httprequest.headers
        )



        webhook = request.env[
            "sce.webhook"
        ].sudo().create({

            "connector":

                connector,

            "payload":

                payload,

            "headers":

                headers,

        })



        webhook.dispatch()



        return request.make_response(

            json.dumps({

                "success":
                    True,

                "id":
                    webhook.id,

            }),

            headers=[

                (
                    "Content-Type",
                    "application/json",
                )

            ],

        )