# -*- coding: utf-8 -*-

"""
SCE Connector Exceptions
"""



class SCEConnectorError(Exception):
    """
    Generic connector error.
    """

    pass



class SCEValidationError(
    SCEConnectorError
):
    """
    Data validation error.
    """

    pass



class SCEMappingError(
    SCEConnectorError
):
    """
    Mapping between systems failed.
    """

    pass



class SCEPublicationError(
    SCEConnectorError
):
    """
    External publication failed.
    """

    pass