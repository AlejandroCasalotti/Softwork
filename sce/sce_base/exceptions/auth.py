# -*- coding: utf-8 -*-

"""
SCE Authentication Exceptions
"""


class SCEAuthenticationError(Exception):
    """
    Generic authentication error.
    """

    pass



class SCETokenExpiredError(
    SCEAuthenticationError
):
    """
    Access token expired.
    """

    pass



class SCETokenRefreshError(
    SCEAuthenticationError
):
    """
    Refresh token failed.
    """

    pass



class SCEPermissionError(
    SCEAuthenticationError
):
    """
    User has insufficient permissions.
    """

    pass