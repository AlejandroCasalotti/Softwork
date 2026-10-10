from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class MarketplaceOrderImportTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connector = cls.env["sce.connector"].create({
            "name": "Order import test",
            "provider_type": "mercadolibre",
        })
        plan = cls.env.ref("softwork_ecommerce_conector_base.sce_subscription_plan_initial")
        subscription = cls.env["sce.subscription"].create({
            "name": "Order import test",
            "partner_id": cls.env.company.partner_id.id,
            "plan_id": plan.id,
        })
        cls.account = cls.env["sce.account"].create({
            "name": "Order import test",
            "connector_id": cls.connector.id,
            "provider_type": "mercadolibre",
            "subscription_id": subscription.id,
        })
        product_template = cls.env["product.template"].create({
            "name": "Mapped order product",
            "type": "consu",
        })
        cls.product = product_template.product_variant_id
        cls.product.default_code = "ORDER-IMPORT-SKU"
        cls.external_order_id = "order-repair-test"
        cls.order_data = {
            "status": "paid",
            "buyer": {"nickname": "Test buyer"},
            "order_items": [{
                "id": "line-repair-test",
                "quantity": 2,
                "unit_price": 12.5,
                "item": {"id": "item-repair-test", "title": "Mapped order product"},
            }],
        }

    def test_reimport_adds_previously_unmapped_order_line(self):
        provider = Mock()
        provider.get_order.return_value = {"order": self.order_data}
        service = self.env["marketplace.publication.service"]

        with patch.object(type(service), "_get_provider_for_account", return_value=provider):
            first_result = service.import_order(self.account, self.external_order_id)
            order = self.env["sale.order"].search([
                ("marketplace_account_id", "=", self.account.id),
                ("marketplace_external_order_id", "=", self.external_order_id),
            ])
            self.assertEqual(first_result["missing_items"], ["item-repair-test"])
            self.assertFalse(order.order_line)
            self.assertEqual(order.state, "draft")

            self.env["marketplace.product.mapping"].create({
                "account_id": self.account.id,
                "product_id": self.product.id,
                "external_id": "item-repair-test",
            })
            second_result = service.import_order(self.account, self.external_order_id)
            service.import_order(self.account, self.external_order_id)

        self.assertFalse(second_result["created"])
        self.assertEqual(second_result["missing_items"], [])
        self.assertEqual(order.order_line.mapped("marketplace_external_line_id"), ["line-repair-test"])
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.product)
        self.assertEqual(order.state, "sale")