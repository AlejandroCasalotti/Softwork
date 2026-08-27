from odoo.tests.common import TransactionCase


class TestSceConnectTenantIsolation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connect_group = cls.env.ref("sce_connect.group_sce_connect_user")
        cls.user_a = cls.env["res.users"].create(
            {
                "name": "SCE Connect User A",
                "login": "sce-connect-user-a",
                "email": "sce-connect-user-a@example.test",
                "groups_id": [(6, 0, [cls.connect_group.id])],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "SCE Connect User B",
                "login": "sce-connect-user-b",
                "email": "sce-connect-user-b@example.test",
                "groups_id": [(6, 0, [cls.connect_group.id])],
            }
        )
        cls.tenant_a = cls.env["sce.tenant"].create(
            {"name": "Tenant A", "code": "tenant-a", "user_ids": [(6, 0, [cls.user_a.id])]}
        )
        cls.tenant_b = cls.env["sce.tenant"].create(
            {"name": "Tenant B", "code": "tenant-b", "user_ids": [(6, 0, [cls.user_b.id])]}
        )
        cls.secret_a = cls.env["sce.secret"].create(
            {"name": "Odoo API key A", "tenant_id": cls.tenant_a.id, "secret_type": "odoo_api_key"}
        )
        cls.secret_b = cls.env["sce.secret"].create(
            {"name": "Odoo API key B", "tenant_id": cls.tenant_b.id, "secret_type": "odoo_api_key"}
        )
        cls.connection_a = cls.env["sce.external.connection"].create(
            {
                "name": "Odoo A",
                "tenant_id": cls.tenant_a.id,
                "url": "https://odoo-a.example.test",
                "database": "db-a",
                "user": "bot-a@example.test",
                "secret_id": cls.secret_a.id,
            }
        )
        cls.connection_b = cls.env["sce.external.connection"].create(
            {
                "name": "Odoo B",
                "tenant_id": cls.tenant_b.id,
                "url": "https://odoo-b.example.test",
                "database": "db-b",
                "user": "bot-b@example.test",
                "secret_id": cls.secret_b.id,
            }
        )

    def test_user_a_cannot_read_tenant_b_data(self):
        tenant_ids = self.env["sce.tenant"].with_user(self.user_a).search([])
        connection_ids = self.env["sce.external.connection"].with_user(self.user_a).search([])
        secret_ids = self.env["sce.secret"].with_user(self.user_a).search([])
        self.assertEqual(tenant_ids, self.tenant_a)
        self.assertEqual(connection_ids, self.connection_a)
        self.assertEqual(secret_ids, self.secret_a)

    def test_user_b_cannot_read_tenant_a_data(self):
        tenant_ids = self.env["sce.tenant"].with_user(self.user_b).search([])
        connection_ids = self.env["sce.external.connection"].with_user(self.user_b).search([])
        secret_ids = self.env["sce.secret"].with_user(self.user_b).search([])
        self.assertEqual(tenant_ids, self.tenant_b)
        self.assertEqual(connection_ids, self.connection_b)
        self.assertEqual(secret_ids, self.secret_b)
