# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Attribute Service

Provides category attribute management.
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLAttributeService(models.AbstractModel):
    """
    Mercado Libre Attribute Service.
    """

    _name = "ml.attribute.service"
    _description = "Mercado Libre Attribute Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _category_service(self):
        return self.env["ml.category.service"]

    # -------------------------------------------------------------------------
    # Attributes
    # -------------------------------------------------------------------------

    def get_attributes(
        self,
        account,
        category_id,
    ):
        """
        Returns category attributes.
        """

        return self._category_service().attributes(
            account,
            category_id,
        )

    # -------------------------------------------------------------------------
    # Required Attributes
    # -------------------------------------------------------------------------

    def required(
        self,
        account,
        category_id,
    ):
        """
        Returns required attributes.
        """

        attributes = self.get_attributes(
            account,
            category_id,
        )

        return [
            attribute
            for attribute in attributes
            if attribute.get("tags", {}).get("required")
        ]

    # -------------------------------------------------------------------------
    # Optional Attributes
    # -------------------------------------------------------------------------

    def optional(
        self,
        account,
        category_id,
    ):
        """
        Returns optional attributes.
        """

        attributes = self.get_attributes(
            account,
            category_id,
        )

        return [
            attribute
            for attribute in attributes
            if not attribute.get("tags", {}).get("required")
        ]

    # -------------------------------------------------------------------------
    # Attribute
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns one attribute.
        """

        attributes = self.get_attributes(
            account,
            category_id,
        )

        for attribute in attributes:

            if attribute["id"] == attribute_id:
                return attribute

        return {}

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(
        self,
        account,
        category_id,
        values,
    ):
        """
        Validates required attributes.
        """

        errors = []

        required = self.required(
            account,
            category_id,
        )

        for attribute in required:

            attribute_id = attribute["id"]

            if attribute_id not in values:

                errors.append(

                    {
                        "attribute": attribute_id,
                        "message": "Required attribute.",
                    }

                )

        return errors

    # -------------------------------------------------------------------------
    # Normalize
    # -------------------------------------------------------------------------

    def normalize(
        self,
        values,
    ):
        """
        Converts dictionary to Mercado Libre format.
        """

        attributes = []

        for key, value in values.items():

            if value in (
                False,
                None,
                "",
            ):
                continue

            attributes.append({

                "id": key,

                "value_name": str(value),

            })

        return attributes

    # -------------------------------------------------------------------------
    # Allowed Values
    # -------------------------------------------------------------------------

    def allowed_values(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns allowed values.
        """

        attribute = self.get(
            account,
            category_id,
            attribute_id,
        )

        return attribute.get(
            "values",
            [],
        )

    # -------------------------------------------------------------------------
    # Is Required
    # -------------------------------------------------------------------------

    def is_required(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns True if attribute is mandatory.
        """

        attribute = self.get(
            account,
            category_id,
            attribute_id,
        )

        return bool(

            attribute.get(
                "tags",
                {},
            ).get(
                "required"
            )

        )

    # -------------------------------------------------------------------------
    # Is Variation
    # -------------------------------------------------------------------------

    def is_variation(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns True if attribute
        defines variations.
        """

        attribute = self.get(
            account,
            category_id,
            attribute_id,
        )

        return bool(

            attribute.get(
                "tags",
                {},
            ).get(
                "allow_variations"
            )

        )

    # -------------------------------------------------------------------------
    # Units
    # -------------------------------------------------------------------------

    def units(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns allowed units.
        """

        attribute = self.get(
            account,
            category_id,
            attribute_id,
        )

        return attribute.get(
            "units",
            [],
        )

    # -------------------------------------------------------------------------
    # Attribute Name
    # -------------------------------------------------------------------------

    def name(
        self,
        account,
        category_id,
        attribute_id,
    ):
        """
        Returns attribute name.
        """

        attribute = self.get(
            account,
            category_id,
            attribute_id,
        )

        return attribute.get(
            "name",
            "",
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search(
        self,
        account,
        category_id,
        text,
    ):
        """
        Searches attributes by name.
        """

        text = text.lower()

        attributes = self.get_attributes(
            account,
            category_id,
        )

        return [

            attribute

            for attribute in attributes

            if text in attribute.get(
                "name",
                "",
            ).lower()

        ]