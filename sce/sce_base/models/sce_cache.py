# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Cache Storage Model
"""


from odoo import (
    api,
    fields,
    models,
)



class SCECache(models.Model):

    """
    Persistent cache storage.

    Used by SCE services to store
    temporary external data.
    """


    _name = "sce.cache"

    _description = "SCE Cache"

    _order = "create_date desc"



    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    key = fields.Char(

        string="Cache Key",

        required=True,

        index=True,

    )



    value = fields.Text(

        string="Cached Value",

        required=True,

    )



    # -------------------------------------------------------------------------
    # Expiration
    # -------------------------------------------------------------------------

    expiration = fields.Datetime(

        string="Expiration Date",

        index=True,

    )



    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_id = fields.Many2one(

        "sce.account",

        string="Account",

        ondelete="cascade",

        index=True,

    )



    company_id = fields.Many2one(

        "res.company",

        string="Company",

        default=lambda self: self.env.company,

        index=True,

    )



    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    namespace = fields.Char(

        string="Namespace",

        default="default",

        index=True,

        help="Logical cache group.",

    )



    cache_type = fields.Selection(

        [

            (
                "api",
                "API Response",
            ),

            (
                "token",
                "Authentication Token",
            ),

            (
                "mapping",
                "Mapping Data",
            ),

            (
                "system",
                "System Data",
            ),

        ],

        string="Cache Type",

        default="system",

        index=True,

    )



    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    active = fields.Boolean(

        string="Active",

        default=True,

    )



    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def is_expired(self):

        """
        Checks if cache entry expired.
        """


        self.ensure_one()


        if not self.expiration:

            return False



        return (

            self.expiration

            <

            fields.Datetime.now()

        )



    @api.model
    def cleanup_expired(self):

        """
        Removes expired cache entries.
        """


        records = self.search(

            [

                (

                    "expiration",

                    "<",

                    fields.Datetime.now(),

                )

            ]

        )


        records.unlink()


        return True



    @api.model
    def get_valid(
        self,
        key,
        account=None,
    ):
        """
        Returns valid cache record.
        """


        domain = [

            (

                "key",

                "=",

                key,

            )

        ]



        if account:

            domain.append(

                (

                    "account_id",

                    "=",

                    account.id,

                )

            )



        record = self.search(

            domain,

            limit=1,

        )



        if not record:

            return False



        if record.is_expired():

            record.unlink()

            return False



        return record



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _key_account_unique = models.Constraint(
        "UNIQUE(key, account_id)",
        "Cache key must be unique per account.",
    )