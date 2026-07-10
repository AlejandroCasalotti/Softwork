# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Utils Service
"""


import json
import hashlib
import re


from datetime import datetime


from odoo import (
    api,
    models,
    fields,
)



class SCEUtilsService(models.AbstractModel):

    _name = "sce.utils.service"

    _description = "SCE Utils Service"



    # -------------------------------------------------------------------------
    # JSON
    # -------------------------------------------------------------------------

    @api.model
    def json_encode(
        self,
        value,
    ):
        """
        Safe JSON encoder.
        """

        return json.dumps(

            value,

            ensure_ascii=False,

            default=str,

        )



    # -------------------------------------------------------------------------

    @api.model
    def json_decode(
        self,
        value,
        default=None,
    ):
        """
        Safe JSON decoder.
        """


        if not value:

            return default



        try:

            return json.loads(
                value
            )


        except Exception:

            return default



    # -------------------------------------------------------------------------
    # Hash
    # -------------------------------------------------------------------------

    @api.model
    def hash(
        self,
        value,
    ):
        """
        Generates SHA256 hash.
        """


        if isinstance(
            value,
            dict,
        ):

            value = self.json_encode(
                value
            )


        return hashlib.sha256(

            str(value)
            .encode(
                "utf-8"
            )

        ).hexdigest()



    # -------------------------------------------------------------------------
    # Text
    # -------------------------------------------------------------------------

    @api.model
    def clean_text(
        self,
        value,
    ):
        """
        Removes invalid characters.
        """


        if not value:

            return ""


        value = str(value)


        value = re.sub(

            r"\s+",

            " ",

            value,

        )


        return value.strip()



    # -------------------------------------------------------------------------
    # Slug
    # -------------------------------------------------------------------------

    @api.model
    def slug(
        self,
        value,
    ):
        """
        Generates URL friendly text.
        """


        value = self.clean_text(
            value
        )


        value = value.lower()


        value = re.sub(

            r"[^a-z0-9]+",

            "-",

            value,

        )


        return value.strip("-")



    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------

    @api.model
    def parse_date(
        self,
        value,
    ):
        """
        Converts external dates.
        """


        if not value:

            return False



        if isinstance(
            value,
            datetime,
        ):

            return value



        formats = [

            "%Y-%m-%d",

            "%Y-%m-%dT%H:%M:%S",

            "%Y-%m-%dT%H:%M:%SZ",

            "%d/%m/%Y",

        ]



        for fmt in formats:

            try:

                return datetime.strptime(

                    value,

                    fmt,

                )


            except Exception:

                continue



        return False



    # -------------------------------------------------------------------------
    # Datetime Format
    # -------------------------------------------------------------------------

    @api.model
    def format_datetime(
        self,
        value,
    ):

        if not value:

            return False



        return fields.Datetime.to_string(
            value
        )



    # -------------------------------------------------------------------------
    # Compare Dictionaries
    # -------------------------------------------------------------------------

    @api.model
    def compare_dict(
        self,
        first,
        second,
    ):
        """
        Compares two dictionaries.
        """


        return (

            self.json_encode(
                first
            )

            ==

            self.json_encode(
                second
            )

        )



    # -------------------------------------------------------------------------
    # Deep Get
    # -------------------------------------------------------------------------

    @api.model
    def deep_get(
        self,
        data,
        path,
        default=None,
    ):
        """
        Gets nested dictionary values.

        Example:
        deep_get(data,"user.id")
        """


        current = data


        for key in path.split("."):


            if not isinstance(
                current,
                dict,
            ):

                return default



            current = current.get(
                key
            )


            if current is None:

                return default



        return current



    # -------------------------------------------------------------------------
    # Chunk List
    # -------------------------------------------------------------------------

    @api.model
    def chunks(
        self,
        values,
        size,
    ):
        """
        Splits list into chunks.
        """


        return [

            values[i:i + size]

            for i in range(
                0,
                len(values),
                size,
            )

        ]