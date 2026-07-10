# -*- coding: utf-8 -*-

"""
SCE API Exceptions
"""



class SCEAPIError(Exception):
    """
    Generic API error.
    """

    pass




class SCEConnectionError(SCEAPIError):
    """
    Connection failure.
    """

    pass