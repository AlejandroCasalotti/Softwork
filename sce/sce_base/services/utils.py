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

        return json.dumps(

            value,

            ensure_ascii=False,

            sort_keys=True,

            default=str,

        )



    @api.model
    def json_decode(
        self,
        value,
        default=None,
    ):


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


        if not value:

            return ""


        value = str(value)


        value = re.sub(
            r"\s+",
            " ",
            value,
        )


        return value.strip()



    @api.model
    def normalize_text(
        self,
        value,
    ):
        """
        Normalizes external text.
        """

        value = self.clean_text(
            value
        )

        return value.lower()



    # -------------------------------------------------------------------------
    # Slug
    # -------------------------------------------------------------------------

    @api.model
    def slug(
        self,
        value,
    ):

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
    # Format Datetime
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
    # Compare
    # -------------------------------------------------------------------------

    @api.model
    def compare_dict(
        self,
        first,
        second,
    ):

        return (
            self.json_encode(first)
            ==
            self.json_encode(second)
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


        current = data


        for key in path.split("."):


            if isinstance(
                current,
                list,
            ):

                try:

                    current = current[
                        int(key)
                    ]

                except Exception:

                    return default


                continue



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
    # Type Helpers
    # -------------------------------------------------------------------------

    @api.model
    def to_bool(
        self,
        value,
    ):

        return str(value).lower() in (
            "true",
            "1",
            "yes",
            "y",
        )



    @api.model
    def to_int(
        self,
        value,
        default=0,
    ):

        try:

            return int(value)

        except Exception:

            return default



    @api.model
    def to_float(
        self,
        value,
        default=0.0,
    ):

        try:

            return float(value)

        except Exception:

            return default



    # -------------------------------------------------------------------------
    # Chunk
    # -------------------------------------------------------------------------

    @api.model
    def chunks(
        self,
        values,
        size,
    ):

        return [

            values[i:i + size]

            for i in range(
                0,
                len(values),
                size,
            )

        ]