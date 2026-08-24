# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

HTTP Client Library

Generic, connector-agnostic HTTP layer used by
marketplace API clients (e.g. sce_connector_ml).
"""

from .auth import AuthStrategy, BearerAuth
from .response import HttpResponse
from .client import HttpClient

__all__ = [
    "AuthStrategy",
    "BearerAuth",
    "HttpResponse",
    "HttpClient",
]
