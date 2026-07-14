# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Queue Exceptions
"""


from .base import SCEException



class SCEQueueError(SCEException):
    """
    Generic queue error.

    Base exception for queue
    and background execution failures.
    """

    def __init__(
        self,
        message,
        job_id=None,
        queue=None,
        operation=None,
        provider=None,
        model=None,
        record_id=None,
    ):
        super().__init__(message)

        self.message = message
        self.job_id = job_id
        self.queue = queue
        self.operation = operation
        self.provider = provider
        self.model = model
        self.record_id = record_id

    def __str__(self):
        return self.message



class SCEJobError(
    SCEQueueError
):
    """
    Job execution failed.

    Example:
    Product synchronization job failed.
    """

    pass



class SCERetryLimitError(
    SCEQueueError
):
    """
    Maximum retries reached.

    Example:
    Job failed after 5 attempts.
    """

    pass



class SCEExecutionError(
    SCEQueueError
):
    """
    Generic execution failure.

    Example:
    Unexpected runtime error.
    """

    pass



class SCEJobTimeoutError(
    SCEQueueError
):
    """
    Job exceeded maximum execution time.

    Example:
    API request hanging indefinitely.
    """

    pass



class SCEJobCancelledError(
    SCEQueueError
):
    """
    Job was manually cancelled.
    """

    pass