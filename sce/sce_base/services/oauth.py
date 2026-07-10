# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

OAuth Service
"""

import time
import requests


from odoo import (
    api,
    models,
    fields,
)


from ..exceptions import (
    SCEAuthenticationError,
    SCEConnectionError,
)



class SCEOAuthService(models.AbstractModel):

    _name = "sce.oauth.service"

    _description = "SCE OAuth Service"



    # -------------------------------------------------------------------------
    # Authorization URL
    # -------------------------------------------------------------------------

    @api.model
    def get_authorization_url(
        self,
        account,
        state=None,
    ):
        """
        Generates OAuth authorization URL.
        """


        if not account.oauth_authorization_url:

            raise SCEAuthenticationError(
                "OAuth authorization URL not configured."
            )


        params = {

            "client_id":
                account.oauth_client_id,

            "response_type":
                "code",

            "redirect_uri":
                account.oauth_redirect_uri,

        }


        if state:

            params["state"] = state



        from urllib.parse import urlencode


        return (

            account.oauth_authorization_url

            +

            "?"

            +

            urlencode(params)

        )



    # -------------------------------------------------------------------------
    # Exchange Code
    # -------------------------------------------------------------------------

    @api.model
    def exchange_code(
        self,
        account,
        code,
    ):
        """
        Exchanges authorization code for tokens.
        """


        if not account.oauth_token_url:

            raise SCEAuthenticationError(
                "OAuth token URL not configured."
            )


        payload = {

            "grant_type":
                "authorization_code",

            "client_id":
                account.oauth_client_id,

            "client_secret":
                account.oauth_client_secret,

            "code":
                code,

            "redirect_uri":
                account.oauth_redirect_uri,

        }



        try:


            response = requests.post(

                account.oauth_token_url,

                data=payload,

                timeout=30,

            )


        except requests.exceptions.RequestException as error:


            raise SCEConnectionError(
                str(error)
            )



        data = self._parse_response(
            response
        )


        self.save_tokens(
            account,
            data,
        )


        return data



    # -------------------------------------------------------------------------
    # Refresh Token
    # -------------------------------------------------------------------------

    @api.model
    def refresh_token(
        self,
        account,
    ):
        """
        Refresh expired access token.
        """


        if not account.oauth_refresh_token:

            raise SCEAuthenticationError(
                "Refresh token missing."
            )



        payload = {

            "grant_type":
                "refresh_token",

            "client_id":
                account.oauth_client_id,

            "client_secret":
                account.oauth_client_secret,

            "refresh_token":
                account.oauth_refresh_token,

        }



        try:


            response = requests.post(

                account.oauth_token_url,

                data=payload,

                timeout=30,

            )


        except requests.exceptions.RequestException as error:


            raise SCEConnectionError(
                str(error)
            )



        data = self._parse_response(
            response
        )


        self.save_tokens(
            account,
            data,
        )


        return data



    # -------------------------------------------------------------------------
    # Save Tokens
    # -------------------------------------------------------------------------

    @api.model
    def save_tokens(
        self,
        account,
        data,
    ):
        """
        Stores OAuth tokens.
        """


        values = {

            "oauth_access_token":

                data.get(
                    "access_token"
                ),


            "oauth_refresh_token":

                data.get(
                    "refresh_token",
                    account.oauth_refresh_token,
                ),


        }



        if data.get(
            "expires_in"
        ):


            values[
                "oauth_token_expiration"
            ] = fields.Datetime.now() + fields.DateUtils.relativedelta(

                seconds=data.get(
                    "expires_in"
                )

            )



        account.write(
            values
        )


        return True



    # -------------------------------------------------------------------------
    # Token Validation
    # -------------------------------------------------------------------------

    @api.model
    def token_valid(
        self,
        account,
    ):
        """
        Checks if token is still valid.
        """


        if not account.oauth_access_token:

            return False



        if not account.oauth_token_expiration:

            return True



        return (

            account.oauth_token_expiration

            >

            fields.Datetime.now()

        )



    # -------------------------------------------------------------------------
    # Get Access Token
    # -------------------------------------------------------------------------

    @api.model
    def get_access_token(
        self,
        account,
    ):
        """
        Returns valid access token.
        """


        if self.token_valid(
            account
        ):

            return account.oauth_access_token



        self.refresh_token(
            account
        )


        return account.oauth_access_token



    # -------------------------------------------------------------------------
    # Response
    # -------------------------------------------------------------------------

    def _parse_response(
        self,
        response,
    ):


        if response.status_code >= 400:

            raise SCEAuthenticationError(

                response.text

            )



        return response.json()