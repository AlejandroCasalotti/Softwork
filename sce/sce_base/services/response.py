# -*- coding: utf-8 -*-

from __future__ import annotations

import time


class RetryService:
    """
    Simple retry helper with exponential backoff.
    """

    def execute(
        self,
        func,
        *args,
        retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions=(Exception,),
        **kwargs,
    ):
        current_delay = delay

        for attempt in range(1, retries + 1):
            try:
                return func(*args, **kwargs)

            except exceptions:
                if attempt >= retries:
                    raise

                time.sleep(current_delay)
                current_delay *= backoff