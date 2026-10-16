"""Run with Odoo --test-enable -i massive_assistant on each supported version."""
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


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
