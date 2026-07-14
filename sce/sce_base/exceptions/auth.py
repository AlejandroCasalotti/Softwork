# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Authentication Exceptions
"""


from .base import SCEException



class SCEAuthenticationError(SCEException):
    """
    Generic authentication error.

    Base exception for authentication failures.
    """

    def __init__(
        self,
        message,
        provider=None,
        account=None,
    ):
        super().__init__(message)

        self.message = message
        self.provider = provider
        self.account = account

    def __str__(self):
        return self.message



class SCEAuthorizationError(
    SCEAuthenticationError
):
    """
    Authorization flow failed.

    Used when the initial OAuth authorization
    process fails.
    """

    pass



class SCETokenExpiredError(
    SCEAuthenticationError
):
    """
    Access token expired.

    Usually handled automatically by
    refreshing the token.
    """

    pass



class SCETokenRefreshError(
    SCEAuthenticationError
):
    """
    Refresh token failed.

    Requires user authorization again.
    """

    pass



class SCEPermissionError(
    SCEAuthenticationError
):
    """
    User has insufficient permissions.

    Example:
    Missing provider scopes.
    """

    pass