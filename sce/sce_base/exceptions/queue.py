# -*- coding: utf-8 -*-

"""
SCE Queue Exceptions
"""



class SCEQueueError(Exception):
    """
    Generic queue error.
    """

    pass



class SCEJobError(
    SCEQueueError
):
    """
    Job execution failed.
    """

    pass



class SCERetryLimitError(
    SCEQueueError
):
    """
    Maximum retries reached.
    """

    pass



class SCEExecutionError(
    SCEQueueError
):
    """
    Generic execution failure.
    """

    pass