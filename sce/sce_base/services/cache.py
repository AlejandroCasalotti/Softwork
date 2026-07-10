# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Cache Service
"""


import hashlib
import json


from datetime import timedelta


from odoo import (
    api,
    fields,
    models,
)



class SCECacheService(models.AbstractModel):

    _name = "sce.cache.service"

    _description = "SCE Cache Service"



    # -------------------------------------------------------------------------
    # Set Value
    # -------------------------------------------------------------------------

    @api.model
    def set(
        self,
        key,
        value,
        ttl=3600,
        account=None,
    ):
        """
        Stores cached value.
        """


        cache_key = self._build_key(

            key,

            account,

        )


        expiration = (

            fields.Datetime.now()

            +

            timedelta(
                seconds=ttl
            )

        )


        record = self.env[
            "sce.cache"
        ].search(

            [

                (
                    "key",
                    "=",
                    cache_key,
                )

            ],

            limit=1,

        )


        values = {

            "key":

                cache_key,


            "value":

                json.dumps(
                    value
                ),


            "expiration":

                expiration,

        }



        if record:

            record.write(
                values
            )

        else:

            self.env[
                "sce.cache"
            ].create(
                values
            )


        return True



    # -------------------------------------------------------------------------
    # Get Value
    # -------------------------------------------------------------------------

    @api.model
    def get(
        self,
        key,
        default=None,
        account=None,
    ):
        """
        Retrieves cached value.
        """


        cache_key = self._build_key(

            key,

            account,

        )


        record = self.env[
            "sce.cache"
        ].search(

            [

                (
                    "key",
                    "=",
                    cache_key,
                )

            ],

            limit=1,

        )


        if not record:

            return default



        if (

            record.expiration

            and

            record.expiration

            <

            fields.Datetime.now()

        ):


            record.unlink()


            return default



        try:

            return json.loads(
                record.value
            )


        except Exception:

            return record.value



    # -------------------------------------------------------------------------
    # Exists
    # -------------------------------------------------------------------------

    @api.model
    def exists(
        self,
        key,
        account=None,
    ):


        return (

            self.get(
                key,
                account=account,
            )

            is not None

        )



    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    @api.model
    def delete(
        self,
        key,
        account=None,
    ):


        cache_key = self._build_key(

            key,

            account,

        )


        records = self.env[
            "sce.cache"
        ].search(

            [

                (
                    "key",
                    "=",
                    cache_key,
                )

            ]

        )


        records.unlink()


        return True



    # -------------------------------------------------------------------------
    # Clear
    # -------------------------------------------------------------------------

    @api.model
    def clear(
        self,
        account=None,
    ):
        """
        Clears cache.
        """


        domain = []


        if account:

            domain.append(

                (
                    "account_id",
                    "=",
                    account.id,
                )

            )


        self.env[
            "sce.cache"
        ].search(
            domain
        ).unlink()


        return True



    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    @api.model
    def cleanup(self):
        """
        Removes expired cache.
        """


        self.env[
            "sce.cache"
        ].search(

            [

                (
                    "expiration",
                    "<",
                    fields.Datetime.now(),
                )

            ]

        ).unlink()


        return True



    # -------------------------------------------------------------------------
    # Key Generator
    # -------------------------------------------------------------------------

    def _build_key(
        self,
        key,
        account=None,
    ):


        value = key


        if account:

            value = (

                "%s:%s"

                %

                (

                    account.id,

                    key,

                )

            )


        return hashlib.sha256(

            value.encode(
                "utf-8"
            )

        ).hexdigest()