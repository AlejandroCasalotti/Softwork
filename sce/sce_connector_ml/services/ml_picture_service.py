# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Picture Service
"""

from __future__ import annotations

import base64
import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)


class MLPictureService(models.AbstractModel):
    """
    Mercado Libre Picture Service.
    """

    _name = "ml.picture.service"
    _description = "Mercado Libre Picture Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Upload
    # -------------------------------------------------------------------------

    def upload(
        self,
        account,
        image,
        filename="image.jpg",
    ):
        """
        Uploads one image to Mercado Libre.
        """

        endpoint = "/pictures"

        if isinstance(image, str):
            image = base64.b64decode(image)

        files = {
            "file": (
                filename,
                image,
                "image/jpeg",
            )
        }

        return self._client().post_multipart(
            account,
            endpoint,
            files=files,
        )

    # -------------------------------------------------------------------------
    # Upload from URL
    # -------------------------------------------------------------------------

    def upload_from_url(
        self,
        account,
        url,
    ):
        """
        Downloads and uploads an image.
        """

        response = requests.get(
            url,
            timeout=60,
        )

        response.raise_for_status()

        return self.upload(
            account,
            response.content,
        )

    # -------------------------------------------------------------------------
    # Upload Product Images
    # -------------------------------------------------------------------------

    def upload_product(
        self,
        account,
        product,
    ):
        """
        Uploads all product images.
        """

        pictures = []

        if product.image_1920:

            result = self.upload(
                account,
                product.image_1920,
                "%s.jpg" % product.default_code,
            )

            if result.get("id"):

                pictures.append(result)

        for image in product.product_template_image_ids:

            if not image.image_1920:
                continue

            result = self.upload(
                account,
                image.image_1920,
                "%s.jpg" % image.name,
            )

            if result.get("id"):

                pictures.append(result)

        return pictures

    # -------------------------------------------------------------------------
    # Build Publication Pictures
    # -------------------------------------------------------------------------

    def publication_payload(
        self,
        account,
        product,
    ):
        """
        Builds Mercado Libre picture payload.
        """

        uploaded = self.upload_product(
            account,
            product,
        )

        payload = []

        for picture in uploaded:

            payload.append({

                "id": picture["id"]

            })

        return payload

    # -------------------------------------------------------------------------
    # Validate
    # -------------------------------------------------------------------------

    def validate(
        self,
        product,
    ):
        """
        Validates product images.
        """

        errors = []

        if not product.image_1920:

            errors.append(
                "Main image is required."
            )

        return errors

    # -------------------------------------------------------------------------
    # Exists
    # -------------------------------------------------------------------------

    def has_images(
        self,
        product,
    ):

        return bool(product.image_1920)

    # -------------------------------------------------------------------------
    # Count
    # -------------------------------------------------------------------------

    def count(
        self,
        product,
    ):

        total = 0

        if product.image_1920:

            total += 1

        total += len(
            product.product_template_image_ids
        )

        return total

    # -------------------------------------------------------------------------
    # Remove
    # -------------------------------------------------------------------------

    def remove_duplicates(
        self,
        pictures,
    ):
        """
        Removes duplicated picture IDs.
        """

        result = []
        ids = set()

        for picture in pictures:

            picture_id = picture.get("id")

            if not picture_id:

                continue

            if picture_id in ids:

                continue

            ids.add(picture_id)

            result.append(picture)

        return result

    # -------------------------------------------------------------------------
    # Public URLs
    # -------------------------------------------------------------------------

    def urls(
        self,
        pictures,
    ):
        """
        Returns picture URLs.
        """

        urls = []

        for picture in pictures:

            if picture.get("secure_url"):

                urls.append(
                    picture["secure_url"]
                )

            elif picture.get("url"):

                urls.append(
                    picture["url"]
                )

        return urls

    # -------------------------------------------------------------------------
    # Build Existing Payload
    # -------------------------------------------------------------------------

    def payload_from_ids(
        self,
        picture_ids,
    ):
        """
        Builds publication payload from
        uploaded picture ids.
        """

        return [

            {
                "id": picture_id
            }

            for picture_id in picture_ids

        ]