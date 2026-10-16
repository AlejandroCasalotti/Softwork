"""Run with Odoo --test-enable -i massive_assistant on each supported version."""
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError


class NativeSessionTests(TransactionCase):
    def test_encrypted_pairing_has_no_plaintext_secret(self):
        session=self.env['massive.assistant.session'].sudo().create({'user_id':self.env.uid,'expires_at':fields.Datetime.now()+timedelta(minutes=15)})
        session._save({'secret':'local-only-test-secret','uid':self.env.uid})
        self.assertNotIn('local-only-test-secret',session.sealed)
        self.assertEqual(session._load()['uid'],self.env.uid)

    def test_expired_session_cannot_load_credentials(self):
        session=self.env['massive.assistant.session'].sudo().create({'user_id':self.env.uid,'expires_at':fields.Datetime.now()-timedelta(seconds=1)})
        session._save({'secret':'expired'})
        with self.assertRaises(UserError):session._load()

    def test_internal_sessions_are_not_accessible_to_assistant_users(self):
        user=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Assistant access test','login':'massive-native-acl-test','group_ids' if hasattr(self.env['res.users'],'group_ids') else 'groups_id':[(6,0,[self.env.ref('base.group_user').id,self.env.ref('massive_assistant.group_massive_assistant_user').id])]})
        session=self.env['massive.assistant.session'].sudo().create({'user_id':user.id,'expires_at':fields.Datetime.now()+timedelta(minutes=15)})
        with self.assertRaises(AccessError):session.with_user(user).read(['user_id'])

    def test_one_session_per_user_is_enforced_by_database(self):
        from psycopg2 import IntegrityError
        values={'user_id':self.env.uid,'expires_at':fields.Datetime.now()+timedelta(minutes=15)}
        self.env['massive.assistant.session'].sudo().create(values)
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['massive.assistant.session'].sudo().create(values)
            self.env.flush_all()
