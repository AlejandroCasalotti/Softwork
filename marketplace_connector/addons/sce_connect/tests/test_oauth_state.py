from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase

from ..services.oauth_state import OAuthStateService


class FakeSecretStorage:
    def encrypt(self, value):
        return value


class TestSceOAuthState(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.other_user = self.env["res.users"].create(
            {
                "name": "OAuth Other User",
                "login": "oauth-other-user",
                "email": "oauth-other-user@example.test",
            }
        )
        self.tenant = self.env["sce.tenant"].create(
            {"name": "OAuth Tenant", "code": "oauth-tenant", "user_ids": [(6, 0, [self.user.id])]}
        )
        self.account = self.env["sce.mercadolibre.account"].create(
            {"name": "OAuth Seller", "tenant_id": self.tenant.id}
        )
        self.storage = FakeSecretStorage()

    @patch("odoo.addons.sce_connect.models.sce_secret.SecretStorage.from_environment")
    def test_state_is_bound_and_single_use(self, model_storage_factory):
        model_storage_factory.return_value = self.storage
        state, challenge, transaction = OAuthStateService(self.env).create(
            self.tenant, self.account, self.user
        )
        self.assertTrue(state)
        self.assertTrue(challenge)
        self.assertEqual(transaction.status, "pending")
        consumed = OAuthStateService(self.env).validate_and_consume(state, self.user)
        self.assertEqual(consumed, transaction)
        with self.assertRaises(UserError):
            OAuthStateService(self.env).validate_and_consume(state, self.user)

    @patch("odoo.addons.sce_connect.models.sce_secret.SecretStorage.from_environment")
    def test_state_rejects_wrong_user(self, model_storage_factory):
        model_storage_factory.return_value = self.storage
        state, _challenge, _transaction = OAuthStateService(self.env).create(
            self.tenant, self.account, self.user
        )
        with self.assertRaises(AccessError):
            OAuthStateService(self.env).validate_and_consume(state, self.other_user)

    @patch("odoo.addons.sce_connect.models.sce_secret.SecretStorage.from_environment")
    def test_expired_state_is_rejected(self, model_storage_factory):
        model_storage_factory.return_value = self.storage
        state, _challenge, transaction = OAuthStateService(self.env).create(
            self.tenant, self.account, self.user
        )
        transaction.write({"expires_at": fields.Datetime.now() - timedelta(minutes=1)})
        with self.assertRaises(UserError):
            OAuthStateService(self.env).validate_and_consume(state, self.user)
