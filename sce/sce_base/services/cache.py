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
                    value,
                    default=str,
                ),


            "expiration":
                expiration,

        }


        if account:

            values[
                "account_id"
            ] = account.id



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
    # Get Or Set
    # -------------------------------------------------------------------------

    @api.model
    def get_or_set(
        self,
        key,
        callback,
        ttl=3600,
        account=None,
    ):
        """
        Returns cache or generates value.
        """


        value = self.get(
            key,
            account=account,
        )


        if value is not None:

            return value



        value = callback()


        self.set(
            key,
            value,
            ttl,
            account,
        )


        return value



    # -------------------------------------------------------------------------
    # Exists
    # -------------------------------------------------------------------------

    @api.model
    def exists(
        self,
        key,
        account=None,
    ):

        return self.get(
            key,
            account=account,
        ) is not None



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


        self.env[
            "sce.cache"
        ].search(

            [
                (
                    "key",
                    "=",
                    cache_key,
                )
            ]

        ).unlink()


        return True



    # -------------------------------------------------------------------------
    # Clear
    # -------------------------------------------------------------------------

    @api.model
    def clear(
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
    def cleanup(
        self,
    ):


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