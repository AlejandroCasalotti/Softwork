# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Product Service
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from odoo import fields


class MLProductService:
    """
    Business logic for Mercado Libre products.
    """

    def __init__(self, env) -> None:
        self.env = env

        self.auth_service = env["sce.ml.auth.service"]

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def publish_product(
        self,
        product,
        account=None,
    ):
        """
        Publish a product in Mercado Libre.
        """

        publication = self._get_publication(
            product,
            account,
        )

        if publication.item_id:
            return self.update_product(
                product,
                publication.account_id,
            )

        payload = self._build_payload(
            product,
        )

        client = self.auth_service.api_client(
            publication.account_id,
        )

        result = client.create_item(
            payload,
        )

        publication.write({
            "item_id": result.get("id"),
            "permalink": result.get("permalink"),
            "status": result.get("status"),
            "listing_type": result.get("listing_type_id"),
            "buying_mode": result.get("buying_mode"),
            "catalog_listing": result.get(
                "catalog_listing",
                False,
            ),
            "published_at": fields.Datetime.now(),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        product.write({
            "ml_sync_status": "published",
            "ml_last_export": fields.Datetime.now(),
            "ml_last_sync": fields.Datetime.now(),
            "ml_last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------

    def update_product(
        self,
        product,
        account=None,
    ):
        """
        Update a published product.
        """

        publication = self._get_publication(
            product,
            account,
        )

        if not publication.item_id:
            return self.publish_product(
                product,
                account,
            )

        payload = self._build_payload(
            product,
        )

        client = self.auth_service.api_client(
            publication.account_id,
        )

        result = client.update_item(
            publication.item_id,
            payload,
        )

        publication.write({
            "status": result.get(
                "status",
                publication.status,
            ),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        product.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------

    def synchronize_publication(
        self,
        publication,
    ):
        """
        Synchronize a publication with Mercado Libre.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        data = client.get_item(
            publication.item_id,
        )

        publication.write({
            "status": data.get("status"),
            "sub_status": ",".join(
                data.get("sub_status", []),
            ),
            "health": data.get("health"),
            "price": data.get("price"),
            "available_quantity": data.get(
                "available_quantity",
            ),
            "sold_quantity": data.get(
                "sold_quantity",
            ),
            "permalink": data.get(
                "permalink",
            ),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        publication.product_tmpl_id.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_sync_status": publication.status,
        })

        return publication

    # -------------------------------------------------------------------------
    # Publication Helpers
    # -------------------------------------------------------------------------

    def _get_publication(
        self,
        product,
        account=None,
    ):

        publication = product.ml_publication_ids

        if account:

            publication = publication.filtered(
                lambda p: p.account_id == account
            )

        if publication:
            return publication[0]

        if account is None:

            account = self.env[
                "sce.ml.account"
            ].search(
                [
                    ("company_id", "=", product.company_id.id),
                    ("connected", "=", True),
                ],
                limit=1,
            )

        if not account:

            raise ValueError(
                "No connected Mercado Libre account found."
            )

        return self.env[
            "sce.ml.publication"
        ].create({
            "product_tmpl_id": product.id,
            "account_id": account.id,
            "title": product.ml_title or product.name,
            "category_id": product.ml_category_id,
            "listing_type": product.ml_listing_type,
            "buying_mode": product.ml_buying_mode,
            "condition": product.ml_condition,
            "currency_id": product.ml_currency_id,
            "price": product.list_price,
            "available_quantity": product.qty_available,
        })

            # -------------------------------------------------------------------------
    # Publication Actions
    # -------------------------------------------------------------------------

    def pause_product(
        self,
        product,
        account=None,
    ):
        """
        Pause a Mercado Libre publication.
        """

        publication = self._get_publication(
            product,
            account,
        )

        return self.pause_publication(
            publication,
        )

    def activate_product(
        self,
        product,
        account=None,
    ):
        """
        Activate a paused publication.
        """

        publication = self._get_publication(
            product,
            account,
        )

        return self.activate_publication(
            publication,
        )

    def close_product(
        self,
        product,
        account=None,
    ):
        """
        Close a Mercado Libre publication.
        """

        publication = self._get_publication(
            product,
            account,
        )

        return self.close_publication(
            publication,
        )

    # -------------------------------------------------------------------------
    # Price
    # -------------------------------------------------------------------------

    def update_price(
        self,
        product,
        account=None,
    ):
        """
        Updates the product price in Mercado Libre.
        """

        publication = self._get_publication(
            product,
            account,
        )

        return self.update_publication_price(
            publication,
        )

    # -------------------------------------------------------------------------
    # Stock
    # -------------------------------------------------------------------------

    def update_stock(
        self,
        product,
        account=None,
    ):
        """
        Updates the available stock in Mercado Libre.
        """

        publication = self._get_publication(
            product,
            account,
        )

        return self.update_publication_stock(
            publication,
        )

    # -------------------------------------------------------------------------
    # Publication API
    # -------------------------------------------------------------------------

    def pause_publication(
        self,
        publication,
    ):
        """
        Pause an existing publication.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        response = client.pause_item(
            publication.item_id,
        )

        publication.write({
            "status": response.get(
                "status",
                "paused",
            ),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        publication.product_tmpl_id.write({
            "ml_sync_status": "paused",
            "ml_last_sync": fields.Datetime.now(),
        })

        return publication

    def activate_publication(
        self,
        publication,
    ):
        """
        Activate a paused publication.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        response = client.activate_item(
            publication.item_id,
        )

        publication.write({
            "status": response.get(
                "status",
                "active",
            ),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        publication.product_tmpl_id.write({
            "ml_sync_status": "published",
            "ml_last_sync": fields.Datetime.now(),
        })

        return publication

    def close_publication(
        self,
        publication,
    ):
        """
        Close an existing publication.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        response = client.close_item(
            publication.item_id,
        )

        publication.write({
            "status": response.get(
                "status",
                "closed",
            ),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        publication.product_tmpl_id.write({
            "ml_sync_status": "closed",
            "ml_last_sync": fields.Datetime.now(),
        })

        return publication

    # -------------------------------------------------------------------------
    # Publication Price
    # -------------------------------------------------------------------------

    def update_publication_price(
        self,
        publication,
    ):
        """
        Updates the publication price.
        """

        product = publication.product_tmpl_id

        client = self.auth_service.api_client(
            publication.account_id,
        )

        client.update_price(
            publication.item_id,
            product.list_price,
        )

        publication.write({
            "price": product.list_price,
            "last_price_sync": fields.Datetime.now(),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        product.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------
    # Publication Stock
    # -------------------------------------------------------------------------

    def update_publication_stock(
        self,
        publication,
    ):
        """
        Updates the publication stock.
        """

        product = publication.product_tmpl_id

        client = self.auth_service.api_client(
            publication.account_id,
        )

        client.update_stock(
            publication.item_id,
            int(product.qty_available),
        )

        publication.write({
            "available_quantity": int(
                product.qty_available
            ),
            "last_stock_sync": fields.Datetime.now(),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        product.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_last_error": False,
        })

        return publication

            # -------------------------------------------------------------------------
    # Description
    # -------------------------------------------------------------------------

    def update_description(
        self,
        product,
        account=None,
    ):
        """
        Updates the Mercado Libre description.
        """

        publication = self._get_publication(
            product,
            account,
        )

        client = self.auth_service.api_client(
            publication.account_id,
        )

        client.update_description(
            publication.item_id,
            product.ml_description or "",
        )

        publication.write({
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        product.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------
    # Publication Synchronization
    # -------------------------------------------------------------------------

    def refresh_publication(
        self,
        publication,
    ):
        """
        Refreshes the publication information.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        data = client.get_item(
            publication.item_id,
        )

        publication.write({
            "title": data.get("title"),
            "status": data.get("status"),
            "sub_status": ",".join(
                data.get("sub_status", [])
            ),
            "price": data.get("price"),
            "currency_id": data.get("currency_id"),
            "available_quantity": data.get(
                "available_quantity"
            ),
            "sold_quantity": data.get(
                "sold_quantity"
            ),
            "permalink": data.get("permalink"),
            "listing_type": data.get(
                "listing_type_id"
            ),
            "buying_mode": data.get(
                "buying_mode"
            ),
            "catalog_listing": data.get(
                "catalog_listing",
                False,
            ),
            "health": data.get("health"),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------
    # Questions
    # -------------------------------------------------------------------------

    def synchronize_questions(
        self,
        publication,
    ):
        """
        Synchronizes publication questions.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        questions = client.get_questions(
            publication.item_id,
        )

        publication.write({
            "question_count": len(questions),
            "last_sync_at": fields.Datetime.now(),
        })

        return questions

    def answer_question(
        self,
        publication,
        question_id: str,
        answer: str,
    ):
        """
        Answers a Mercado Libre question.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        return client.answer_question(
            question_id,
            answer,
        )

    # -------------------------------------------------------------------------
    # Visits
    # -------------------------------------------------------------------------

    def synchronize_visits(
        self,
        publication,
    ):
        """
        Synchronizes publication visits.
        """

        client = self.auth_service.api_client(
            publication.account_id,
        )

        visits = client.get_visits(
            publication.item_id,
        )

        publication.write({
            "visit_count": visits.get(
                "total_visits",
                0,
            ),
            "last_sync_at": fields.Datetime.now(),
        })

        return visits

    # -------------------------------------------------------------------------
    # Complete Synchronization
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        product,
        account=None,
    ):
        """
        Executes a complete synchronization.
        """

        publication = self._get_publication(
            product,
            account,
        )

        self.refresh_publication(
            publication,
        )

        self.synchronize_questions(
            publication,
        )

        self.synchronize_visits(
            publication,
        )

        publication.write({
            "sync_status": "success",
            "last_sync_at": fields.Datetime.now(),
        })

        product.write({
            "ml_last_sync": fields.Datetime.now(),
            "ml_sync_status": publication.status,
            "ml_last_error": False,
        })

        return publication

    # -------------------------------------------------------------------------
    # Synchronization Helpers
    # -------------------------------------------------------------------------

    def synchronize_all(
        self,
        account,
    ):
        """
        Synchronizes every publication of an account.
        """

        publications = self.env[
            "sce.ml.publication"
        ].search([
            ("account_id", "=", account.id),
            ("active", "=", True),
        ])

        for publication in publications:
            self.synchronize_publication(
                publication,
            )

        return publications

            # -------------------------------------------------------------------------
    # Payload Builder
    # -------------------------------------------------------------------------

    def _build_payload(
        self,
        product,
    ) -> dict[str, Any]:
        """
        Builds the Mercado Libre payload from an Odoo product.
        """

        return {
            "title": product.ml_title or product.name,
            "category_id": product.ml_category_id,
            "price": product.list_price,
            "currency_id": product.ml_currency_id,
            "available_quantity": int(product.qty_available),
            "buying_mode": product.ml_buying_mode,
            "listing_type_id": product.ml_listing_type,
            "condition": product.ml_condition,
            "description": {
                "plain_text": self._description(product),
            },
            "pictures": self._pictures(product),
            "attributes": self._attributes(product),
            "video_id": product.ml_video_id or None,
            "warranty": product.ml_warranty or "",
        }

    # -------------------------------------------------------------------------
    # Description
    # -------------------------------------------------------------------------

    @staticmethod
    def _description(
        product,
    ) -> str:
        """
        Returns the product description.
        """

        return (
            product.ml_description
            or product.description_sale
            or product.description
            or ""
        )

    # -------------------------------------------------------------------------
    # Pictures
    # -------------------------------------------------------------------------

    @staticmethod
    def _pictures(
        product,
    ) -> list[dict[str, Any]]:
        """
        Builds the picture list.
        """

        pictures = []

        for image in product.product_variant_ids.mapped("image_1920"):

            if image:

                pictures.append({
                    "source": image,
                })

        return pictures

    # -------------------------------------------------------------------------
    # Attributes
    # -------------------------------------------------------------------------

    @staticmethod
    def _attributes(
        product,
    ) -> list[dict[str, Any]]:
        """
        Builds Mercado Libre attributes.
        """

        attributes = []

        if product.default_code:

            attributes.append({
                "id": "SELLER_SKU",
                "value_name": product.default_code,
            })

        if product.barcode:

            attributes.append({
                "id": "GTIN",
                "value_name": product.barcode,
            })

        if product.ml_brand:

            attributes.append({
                "id": "BRAND",
                "value_name": product.ml_brand,
            })

        if product.ml_model:

            attributes.append({
                "id": "MODEL",
                "value_name": product.ml_model,
            })

        return attributes

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_product(
        product,
    ) -> None:
        """
        Validates the minimum information required to publish.
        """

        if not product.ml_category_id:
            raise ValueError(
                "Mercado Libre category is required."
            )

        if not product.ml_title:
            raise ValueError(
                "Mercado Libre title is required."
            )

        if product.list_price <= 0:
            raise ValueError(
                "Product price must be greater than zero."
            )

        if product.qty_available < 0:
            raise ValueError(
                "Product stock cannot be negative."
            )

    # -------------------------------------------------------------------------
    # Publication Utilities
    # -------------------------------------------------------------------------

    def publication_exists(
        self,
        product,
        account=None,
    ) -> bool:

        publication = self._get_publication(
            product,
            account,
        )

        return bool(publication.item_id)

    def get_publication(
        self,
        product,
        account=None,
    ):
        """
        Returns the publication associated with the product.
        """

        return self._get_publication(
            product,
            account,
        )

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def publish_products(
        self,
        products,
        account=None,
    ):
        """
        Publishes multiple products.
        """

        publications = self.env["sce.ml.publication"]

        for product in products:

            publications |= self.publish_product(
                product,
                account,
            )

        return publications

    def update_products(
        self,
        products,
        account=None,
    ):
        """
        Updates multiple products.
        """

        publications = self.env["sce.ml.publication"]

        for product in products:

            publications |= self.update_product(
                product,
                account,
            )

        return publications

    def synchronize_products(
        self,
        products,
        account=None,
    ):
        """
        Synchronizes multiple products.
        """

        publications = self.env["sce.ml.publication"]

        for product in products:

            publications |= self.synchronize(
                product,
                account,
            )

        return publications

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def ping(
        self,
        account,
    ) -> bool:
        """
        Checks that the Mercado Libre API is reachable.
        """

        try:

            client = self.auth_service.api_client(
                account,
            )

            client.get_me()

            return True

        except Exception:

            return False