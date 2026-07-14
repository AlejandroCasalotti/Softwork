# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Queue Service
"""


from datetime import timedelta


from odoo import (
    api,
    fields,
    models,
)



from ..exceptions import (
    SCEQueueError,
    SCEJobError,
    SCERetryLimitError,
)



class SCEQueueService(models.AbstractModel):

    _name = "sce.queue.service"

    _description = "SCE Queue Service"



    # -------------------------------------------------------------------------
    # Create Queue Job
    # -------------------------------------------------------------------------

    @api.model
    def enqueue(
        self,
        action,
        payload=None,
        account=None,
        job=None,
        priority="3",
    ):

        values = {

            "action": action,

            "payload": payload or {},

            "priority": priority,

            "state": "pending",

        }


        if account:

            values["account_id"] = account.id


        if job:

            values["job_id"] = job.id


        return self.env[
            "sce.queue"
        ].create(values)



    # -------------------------------------------------------------------------
    # Execute Pending
    # -------------------------------------------------------------------------

    @api.model
    def process_pending(
        self,
        limit=50,
    ):

        queues = self.env[
            "sce.queue"
        ].search(

            [
                (
                    "state",
                    "=",
                    "pending",
                )
            ],

            order=
            "priority asc, create_date asc",

            limit=limit,

        )


        results = []


        for queue in queues:

            try:

                results.append(
                    self.process(queue)
                )


            except Exception as error:

                self.env[
                    "sce.logger.service"
                ].exception(

                    error,

                    category="queue",

                    queue_id=queue.id,

                    action=queue.action,

                )


        return results



    # -------------------------------------------------------------------------
    # Process Item
    # -------------------------------------------------------------------------

    @api.model
    def process(
        self,
        queue,
    ):


        if queue.state != "pending":

            raise SCEQueueError(
                "Queue item is not pending."
            )


        queue.write({

            "state":
                "processing",

            "started_at":
                fields.Datetime.now(),

        })


        try:


            result = self.env[
                "sce.kernel"
            ].execute(

                queue.action,

                queue.payload,

                queue.account_id,

            )


            queue.write({

                "state":
                    "done",

                "finished_at":
                    fields.Datetime.now(),

                "result":
                    result,

            })


            return result



        except Exception as error:


            self.fail(
                queue,
                error,
            )


            raise SCEJobError(
                str(error)
            )



    # -------------------------------------------------------------------------
    # Fail
    # -------------------------------------------------------------------------

    @api.model
    def fail(
        self,
        queue,
        error,
    ):


        retry_count = (
            queue.retry_count + 1
        )


        if retry_count >= queue.max_retry:

            queue.write({

                "state":
                    "failed",

                "error_message":
                    str(error),

                "retry_count":
                    retry_count,

            })


            raise SCERetryLimitError(
                "Maximum retries reached."
            )



        queue.write({

            "state":
                "failed",

            "error_message":
                str(error),

            "retry_count":
                retry_count,

        })


        return True



    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    @api.model
    def retry(
        self,
        queue,
    ):


        queue.write({

            "state":
                "pending",

            "error_message":
                False,

        })


        return True



    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    @api.model
    def cleanup(
        self,
        days=30,
    ):


        limit_date = (

            fields.Datetime.now()

            -
            timedelta(
                days=days
            )

        )


        records = self.env[
            "sce.queue"
        ].search(

            [

                (
                    "state",
                    "=",
                    "done",
                ),

                (
                    "finished_at",
                    "<",
                    limit_date,
                ),

            ]

        )


        records.unlink()


        return True



    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    @api.model
    def statistics(
        self,
        account=None,
    ):


        domain = []


        if account:

            domain.append(

                (
                    "account_id",
                    "=",
                    account.id,
                )

            )


        Queue = self.env[
            "sce.queue"
        ]


        return {

            "pending":
                Queue.search_count(
                    domain +
                    [
                        (
                            "state",
                            "=",
                            "pending",
                        )
                    ]
                ),


            "processing":
                Queue.search_count(
                    domain +
                    [
                        (
                            "state",
                            "=",
                            "processing",
                        )
                    ]
                ),


            "failed":
                Queue.search_count(
                    domain +
                    [
                        (
                            "state",
                            "=",
                            "failed",
                        )
                    ]
                ),

        }