from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class CustomerSecurityTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = new_test_user(
            cls.env, login="sce_isolation_customer",
            groups="base.group_user,softwork_ecommerce_conector_base.group_sce_client_premium",
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Another SCE customer"})
        cls.connector = cls.env["sce.connector"].create({"name": "Test ML", "provider_type": "mercadolibre"})
        plan = cls.env.ref("softwork_ecommerce_conector_base.sce_subscription_plan_initial")
        cls.accounts = cls.env["sce.account"]
        for partner in (cls.customer.partner_id.commercial_partner_id, cls.other_partner):
            subscription = cls.env["sce.subscription"].create({
                "name": partner.name, "partner_id": partner.id, "plan_id": plan.id,
            })
            cls.accounts |= cls.env["sce.account"].create({
                "name": partner.name, "connector_id": cls.connector.id,
                "provider_type": "mercadolibre", "subscription_id": subscription.id,
            })

    def test_shared_company_does_not_grant_other_account(self):
        visible = self.env["sce.account"].with_user(self.customer).search([("id", "in", self.accounts.ids)])
        self.assertEqual(visible.ids, self.accounts[:1].ids)
        with self.assertRaises(AccessError):
            self.accounts[1:].with_user(self.customer).read(["name"])

    def test_oauth_checks_owner_even_with_sudo(self):
        with self.assertRaises(UserError):
            self.accounts[1:].with_user(self.customer).sudo()._check_customer_access()

    def test_customer_cannot_reassign_ownership(self):
        with self.assertRaises(UserError):
            self.accounts[:1].with_user(self.customer).write({"subscription_id": self.accounts[1].subscription_id.id})

    def test_pause_cancels_queued_work(self):
        account = self.accounts[:1]
        job = self.env["sce.job"].create({"name": "Queued sync", "account_id": account.id, "job_type": "sync_products"})
        account.with_user(self.customer).action_pause_sync()
        self.assertTrue(account.sync_paused)
        self.assertEqual(job.state, "cancelled")