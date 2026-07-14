# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

OAuth Service
"""

from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta


from odoo import (
    api,
    models,
    fields,
)


from .api import SCEAPIClient


from ..exceptions import (
    SCEAuthenticationError,
    SCEAuthorizationError,
    SCETokenRefreshError,
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

            raise SCEAuthorizationError(
                message="OAuth authorization URL not configured.",
                provider=self._get_provider(account),
                account=account.id,
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


        return (
            account.oauth_authorization_url
            +
            "?"
            +
            urlencode(params)
        )



    # -------------------------------------------------------------------------
    # Exchange Authorization Code
    # -------------------------------------------------------------------------

    @api.model
    def exchange_code(
        self,
        account,
        code,
    ):
        """
        Exchanges authorization code
        for access and refresh tokens.
        """


        if not account.oauth_token_url:

            raise SCEAuthorizationError(
                message="OAuth token URL not configured.",
                provider=self._get_provider(account),
                account=account.id,
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


        client = self._get_client(
            account
        )


        response = client.post_form(

            account.oauth_token_url,

            data=payload,

        )


        self.save_tokens(
            account,
            response,
        )


        return response



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

            raise SCETokenRefreshError(
                message="Refresh token missing.",
                provider=self._get_provider(account),
                account=account.id,
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


        client = self._get_client(
            account
        )


        try:

            response = client.post_form(

                account.oauth_token_url,

                data=payload,

            )


        except SCEConnectionError:

            raise


        except Exception as error:

            raise SCETokenRefreshError(
                message=str(error),
                provider=self._get_provider(account),
                account=account.id,
            )


        self.save_tokens(
            account,
            response,
        )


        return response



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
            ] = (

                fields.Datetime.now()

                +

                relativedelta(

                    seconds=data.get(
                        "expires_in"
                    )

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
        Checks if access token is valid.
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
    # Helpers
    # -------------------------------------------------------------------------

    def _get_client(
        self,
        account,
    ):
        """
        Returns SCE API client.
        """


        return SCEAPIClient(

            provider=self._get_provider(
                account
            ),

            timeout=30,

        )



    def _get_provider(
        self,
        account,
    ):
        """
        Returns provider name.
        """

        if account.provider_id:

            return account.provider_id.name


        return None