import unittest
from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.softwork_ecommerce_conector_base.controllers.webhook import SceWebhookController


class Accounts(list):
    def filtered(self, predicate):
        return Accounts(record for record in self if predicate(record))


class AccountModel:
    def __init__(self, accounts):
        self.accounts = Accounts(accounts)

    def sudo(self):
        return self

    def search(self, _domain):
        return self.accounts

    def __bool__(self):
        return False


class Environment:
    def __init__(self, model):
        self.model = model

    def __getitem__(self, _key):
        return self.model


class WebhookAccountRoutingTests(unittest.TestCase):
    @staticmethod
    def account(seller_id, token):
        return SimpleNamespace(
            active=True,
            external_user_id=False,
            connect_mercadolibre_account_id=SimpleNamespace(seller_user_id=seller_id),
            credentials_json='{"webhook_token": "%s"}' % token,
        )

    def test_routes_by_marketplace_identity_with_multiple_accounts(self):
        account_a = self.account("seller-a", "token-a")
        account_b = self.account("seller-b", "token-b")
        controller = SceWebhookController()
        request = SimpleNamespace(env=Environment(AccountModel([account_a, account_b])))

        with patch("odoo.addons.softwork_ecommerce_conector_base.controllers.webhook.request", request):
            result = controller._resolve_account("mercadolibre", {"user_id": "seller-b"}, "token-a")

        self.assertEqual(len(result), 1)
        self.assertIs(result[0], account_b)

    def test_ambiguous_webhook_is_not_routed(self):
        account_a = self.account("seller-a", "token-a")
        account_b = self.account("seller-b", "token-b")
        controller = SceWebhookController()
        request = SimpleNamespace(env=Environment(AccountModel([account_a, account_b])))

        with patch("odoo.addons.softwork_ecommerce_conector_base.controllers.webhook.request", request):
            result = controller._resolve_account("mercadolibre", {}, "unknown")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()