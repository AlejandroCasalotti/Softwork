# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Exception Registry
"""


from .api import (
    SCEAPIError,
    SCEConnectionError,
)


from .auth import (
    SCEAuthenticationError,
    SCETokenExpiredError,
)


from .connector import (
    SCEConnectorError,
)


from .queue import (
    SCEQueueError,
    SCEJobError,
)