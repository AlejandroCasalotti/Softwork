# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Exception Registry
"""


from .base import (
    SCEException,
)


from .api import (
    SCEAPIError,
    SCEConnectionError,
)


from .auth import (
    SCEAuthenticationError,
    SCEAuthorizationError,
    SCETokenExpiredError,
    SCETokenRefreshError,
    SCEPermissionError,
)


from .connector import (
    SCEConnectorError,
)


from .queue import (
    SCEQueueError,
    SCEJobError,
    SCERetryLimitError,
)