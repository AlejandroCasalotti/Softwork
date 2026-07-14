# -*- coding: utf-8 -*-

"""
Softwork Commerce Engine (SCE)

Credential Service

Centralized service responsible for managing marketplace
credentials.

This service never implements provider-specific
authentication logic.

Validation and refresh operations are delegated to the
corresponding Provider through the Kernel.
"""

from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import UserError


class SCECredentialService(models.AbstractModel):
    _name = "sce.credential.service"
    _description = "SCE Credential Service"

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    @api.model
    def create(
        self,
        account,
        credential_type,
        data=None,
        metadata=None,
        expires_at=None,
        name=None,
    ):
        """
        Create a new credential.

        Previous active credentials remain stored for audit purposes.
        """

        values = {
            "name": name or f"{account.name} Credential",
            "company_id": account.company_id.id,
            "account_id": account.id,
            "credential_type": credential_type,
            "state": "valid",
            "version": self._next_version(account),
            "data": data or {},
            "metadata": metadata or {},
            "expires_at": expires_at,
        }

        credential = self.env["sce.credential"].sudo().create(values)

        self.env["sce.log.service"].info(
            message="Credential created.",
            category="authentication",
            operation="credential_create",
            account=account,
        )

        return credential

    # ---------------------------------------------------------------------

    @api.model
    def get_active(self, account):
        """
        Returns the newest valid credential.
        """

        return self.env["sce.credential"].search(
            [
                ("account_id", "=", account.id),
                ("state", "=", "valid"),
                ("active", "=", True),
            ],
            order="version desc",
            limit=1,
        )

    # ---------------------------------------------------------------------

    @api.model
    def invalidate(self, credential):

        credential.write({
            "state": "invalid",
        })

        self.env["sce.log.service"].warning(
            message="Credential invalidated.",
            category="authentication",
            operation="credential_invalidate",
            account=credential.account_id,
        )

        return credential

    # ---------------------------------------------------------------------

    @api.model
    def revoke(self, credential):

        credential.write({
            "state": "revoked",
            "active": False,
        })

        self.env["sce.log.service"].warning(
            message="Credential revoked.",
            category="authentication",
            operation="credential_revoke",
            account=credential.account_id,
        )

        return credential

    # ---------------------------------------------------------------------

    @api.model
    def validate(self, account):
        """
        Delegates validation to the Provider.
        """

        plugin = self.env["sce.kernel"].get_plugin(
            account.plugin_code,
        )

        provider = plugin.provider()

        return provider.validate_credentials(account)

    # ---------------------------------------------------------------------

    @api.model
    def refresh(self, account):
        """
        Delegates refresh to the Provider.
        """

        plugin = self.env["sce.kernel"].get_plugin(
            account.plugin_code,
        )

        provider = plugin.provider()

        return provider.refresh_credentials(account)

    # ---------------------------------------------------------------------
    # Internal
    # ---------------------------------------------------------------------

    @api.model
    def _next_version(self, account):

        credential = self.env["sce.credential"].search(
            [
                ("account_id", "=", account.id),
            ],
            order="version desc",
            limit=1,
        )

        if not credential:
            return 1

        return credential.version + 1