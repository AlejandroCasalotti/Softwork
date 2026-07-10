# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Generic API Client Service
"""

import json
import time
import requests


from odoo import api, models


from ..exceptions import (
    SCEAPIError,
    SCEAuthenticationError,
    SCEConnectionError,
)



class SCEAPIService(models.AbstractModel):

    _name = "sce.api.service"

    _description = "SCE API Service"



    # -------------------------------------------------------------------------
    # Request
    # -------------------------------------------------------------------------

    @api.model
    def request(
        self,
        method,
        url,
        headers=None,
        params=None,
        data=None,
        json_data=None,
        timeout=30,
        **kwargs,
    ):
        """
        Generic HTTP request.
        """


        start = time.time()


        headers = headers or {}


        try:


            response = requests.request(

                method=method,

                url=url,

                headers=headers,

                params=params,

                data=data,

                json=json_data,

                timeout=timeout,

                **kwargs,

            )


        except requests.exceptions.Timeout as error:


            raise SCEConnectionError(
                "Connection timeout: %s"
                %
                error
            )


        except requests.exceptions.ConnectionError as error:


            raise SCEConnectionError(
                "Connection failed: %s"
                %
                error
            )



        duration = (
            time.time()
            -
            start
        )


        self._log_request(

            method,

            url,

            response,

            duration,

        )


        return self._parse_response(
            response
        )



    # -------------------------------------------------------------------------
    # GET
    # -------------------------------------------------------------------------

    @api.model
    def get(
        self,
        url,
        **kwargs,
    ):

        return self.request(
            "GET",
            url,
            **kwargs,
        )



    # -------------------------------------------------------------------------
    # POST
    # -------------------------------------------------------------------------

    @api.model
    def post(
        self,
        url,
        **kwargs,
    ):

        return self.request(
            "POST",
            url,
            **kwargs,
        )



    # -------------------------------------------------------------------------
    # PUT
    # -------------------------------------------------------------------------

    @api.model
    def put(
        self,
        url,
        **kwargs,
    ):

        return self.request(
            "PUT",
            url,
            **kwargs,
        )



    # -------------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------------

    @api.model
    def delete(
        self,
        url,
        **kwargs,
    ):

        return self.request(
            "DELETE",
            url,
            **kwargs,
        )



    # -------------------------------------------------------------------------
    # Response Handler
    # -------------------------------------------------------------------------

    def _parse_response(
        self,
        response,
    ):

        if response.status_code in (
            401,
            403,
        ):

            raise SCEAuthenticationError(
                response.text
            )


        if response.status_code >= 400:

            raise SCEAPIError(

                "API Error %s: %s"

                %

                (
                    response.status_code,

                    response.text,

                )

            )


        try:

            return response.json()


        except Exception:

            return response.text



    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    def _log_request(
        self,
        method,
        url,
        response,
        duration,
    ):

        if not self.env:

            return


        try:

            self.env[
                "sce.log"
            ].log_debug(

                "API request executed",

                category="connection",

                metadata={

                    "method":
                        method,

                    "url":
                        url,

                    "status":
                        response.status_code,

                    "duration":
                        duration,

                },

            )


        except Exception:

            pass