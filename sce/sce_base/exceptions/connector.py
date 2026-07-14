# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Connector Exceptions
"""


from .base import SCEException



class SCEConnectorError(SCEException):
    """
    Generic connector error.

    Base exception for marketplace
    and external connector failures.
    """

    def __init__(
        self,
        message,
        provider=None,
        operation=None,
        resource=None,
        external_id=None,
    ):
        super().__init__(message)

        self.message = message
        self.provider = provider
        self.operation = operation
        self.resource = resource
        self.external_id = external_id

    def __str__(self):
        return self.message



class SCEValidationError(
    SCEConnectorError
):
    """
    Data validation error.

    Example:
    Missing required product fields.
    """

    pass



class SCEMappingError(
    SCEConnectorError
):
    """
    Mapping between systems failed.

    Example:
    Odoo field cannot be converted
    to marketplace attribute.
    """

    pass



class SCEPublicationError(
    SCEConnectorError
):
    """
    External publication failed.

    Example:
    Product rejected by marketplace.
    """

    pass



class SCEProviderError(
    SCEConnectorError
):
    """
    External provider rejected request.

    Example:
    Marketplace API returned
    a business rule error.
    """

    pass



class SCESynchronizationError(
    SCEConnectorError
):
    """
    Synchronization process failed.

    Example:
    Product, order or stock sync failed.
    """

    pass