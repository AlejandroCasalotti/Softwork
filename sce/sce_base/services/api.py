# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

API Service

Provides common HTTP/API communication
for all external connectors.
"""


import uuid
import requests


from ..exceptions import (
    SCEAPIError,
    SCEConnectionError,
)



class SCEAPIClient:
    """
    Generic API Client.

    Base HTTP client used by connectors.
    """


    def __init__(
        self,
        base_url=None,
        timeout=30,
        provider=None,
        headers=None,
    ):

        self.base_url = (
            base_url.rstrip("/")
            if base_url
            else ""
        )

        self.timeout = timeout
        self.provider = provider
        self.headers = headers or {}

        self.request_id = str(
            uuid.uuid4()
        )


    # ---------------------------------------------------------
    # URL
    # ---------------------------------------------------------

    def _build_url(
        self,
        endpoint,
    ):

        if endpoint.startswith("http"):
            return endpoint

        return (
            f"{self.base_url}/"
            f"{endpoint.lstrip('/')}"
        )


    # ---------------------------------------------------------
    # Headers
    # ---------------------------------------------------------

    def _get_headers(
        self,
        headers=None,
    ):

        result = {}

        result.update(
            self.headers
        )


        result.setdefault(
            "Accept",
            "application/json",
        )


        result.setdefault(
            "X-SCE-Request-ID",
            self.request_id,
        )


        if headers:
            result.update(
                headers
            )


        return result


    # ---------------------------------------------------------
    # Request
    # ---------------------------------------------------------

    def request(
        self,
        method,
        endpoint,
        params=None,
        data=None,
        json=None,
        headers=None,
    ):

        url = self._build_url(
            endpoint
        )


        request_headers = self._get_headers(
            headers
        )


        try:

            response = requests.request(

                method=method,

                url=url,

                params=params,

                data=data,

                json=json,

                headers=request_headers,

                timeout=self.timeout,

            )


        except requests.exceptions.Timeout:

            raise SCEConnectionError(
                message="API timeout",
                provider=self.provider,
                endpoint=url,
            )


        except requests.exceptions.ConnectionError:

            raise SCEConnectionError(
                message="API connection failed",
                provider=self.provider,
                endpoint=url,
            )


        except Exception as error:

            raise SCEConnectionError(
                message=str(error),
                provider=self.provider,
                endpoint=url,
            )


        return self._handle_response(
            response,
            url,
        )


    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    def _handle_response(
        self,
        response,
        endpoint,
    ):


        if response.status_code >= 400:

            try:

                response_data = response.json()


            except Exception:

                response_data = response.text



            raise SCEAPIError(
                message="API request failed",
                provider=self.provider,
                endpoint=endpoint,
                status_code=response.status_code,
                response=response_data,
            )


        if not response.content:

            return {}


        try:

            return response.json()


        except Exception:

            return response.text


    # ---------------------------------------------------------
    # HTTP Helpers
    # ---------------------------------------------------------

    def get(
        self,
        endpoint,
        **kwargs,
    ):

        return self.request(
            "GET",
            endpoint,
            **kwargs,
        )


    def post(
        self,
        endpoint,
        **kwargs,
    ):

        return self.request(
            "POST",
            endpoint,
            **kwargs,
        )


    def post_form(
        self,
        endpoint,
        data=None,
        **kwargs,
    ):
        """
        POST form encoded data.

        Used mainly by OAuth.
        """

        headers = kwargs.pop(
            "headers",
            {}
        )


        headers.update({

            "Content-Type":
                "application/x-www-form-urlencoded"

        })


        return self.request(
            "POST",
            endpoint,
            data=data,
            headers=headers,
            **kwargs,
        )


    def put(
        self,
        endpoint,
        **kwargs,
    ):

        return self.request(
            "PUT",
            endpoint,
            **kwargs,
        )


    def patch(
        self,
        endpoint,
        **kwargs,
    ):

        return self.request(
            "PATCH",
            endpoint,
            **kwargs,
        )


    def delete(
        self,
        endpoint,
        **kwargs,
    ):

        return self.request(
            "DELETE",
            endpoint,
            **kwargs,
        )