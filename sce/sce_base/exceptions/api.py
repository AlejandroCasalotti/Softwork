# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

API Exceptions
"""


from .base import SCEException



class SCEAPIError(SCEException):
    """
    Generic API error.

    Used for external provider API failures.
    """

    def __init__(
        self,
        message,
        provider=None,
        endpoint=None,
        status_code=None,
        response=None,
    ):
        super().__init__(message)

        self.message = message
        self.provider = provider
        self.endpoint = endpoint
        self.status_code = status_code
        self.response = response

    def __str__(self):
        return self.message



class SCEConnectionError(SCEAPIError):
    """
    Connection failure.

    Used for:
    - timeout
    - DNS errors
    - network failures
    - unavailable services
    """

    pass