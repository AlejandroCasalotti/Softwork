"""Acceptance tests for the general Odoo 19 bridge; no external API calls."""
import unittest
from odoo import release
from odoo.tests.common import TransactionCase


class BusinessTests(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if release.version_info[0]!=19:raise unittest.SkipTest('Odoo 19 bridge only.')
        cls.gateway=cls.env['massive.assistant.gateway']

    def test_default_company_is_resolved_without_browser_context(self):
        result=self.gateway.with_context({}).assistant_capabilities(0)
        self.assertEqual(result['uid'],self.env.uid)
        self.assertEqual(result['company_id'],self.env.user.company_id.id)

    def test_discovery_honors_field_security_and_rejects_technical_models(self):
        result=self.gateway.assistant_discover(self.env.company.id,'res.partner')
        self.assertIn('name',result['fields'])
        users=self.gateway.assistant_discover(self.env.company.id,'res.users')
        self.assertNotIn('password',users['fields']);self.assertFalse(users['access']['write'])
        self.assertTrue(self.gateway.assistant_discover(self.env.company.id,'ir.config_parameter')['rejected'])

    def test_reviewed_create_edit_and_delete(self):
        args={'company_id':self.env.company.id,'model':'res.partner','operation':'create','record_id':0,'values':{'name':'Massive business acceptance'},'action':''}
        preview=self.gateway.business_preview(**args);self.assertIn('token',preview)
        result=self.gateway.business_execute(**args,expected_token=preview['token'])
        self.assertTrue(result['complete']);partner=self.env['res.partner'].browse(result['id'])
        self.assertEqual(partner.company_id,self.env.company)
        args.update(operation='update',record_id=partner.id,values={'phone':'123456'})
        preview=self.gateway.business_preview(**args);self.assertIn('token',preview)
        partner.name='Changed outside the assistant'
        self.assertTrue(self.gateway.business_execute(**args,expected_token=preview['token'])['rejected'])
        preview=self.gateway.business_preview(**args)
        self.assertTrue(self.gateway.business_execute(**args,expected_token=preview['token'])['complete'])
        self.assertEqual(partner.phone,'123456')
        args.update(operation='delete',values={})
        preview=self.gateway.business_preview(**args);self.assertIn('token',preview)
        result=self.gateway.business_execute(**args,expected_token=preview['token'])
        self.assertEqual(result['state'],'deleted');self.assertFalse(partner.exists())

    def test_read_only_user_cannot_create_or_promote_himself(self):
        user=self.env['res.users'].with_context(no_reset_password=True).create({'name':'Massive generic test user','login':'massive-business-ordinary',
            'group_ids':[(6,0,[self.env.ref('massive_assistant.group_massive_assistant_user').id])]})
        gateway=self.gateway.with_user(user)
        result=gateway.business_preview(self.env.company.id,'res.users','create',0,{'name':'Escalate'},'')
        self.assertTrue(result['rejected'])
        # A user lacking create ACL cannot acquire it through the bridge.
        if 'account.move' in self.env and not self.env['account.move'].with_user(user).has_access('create'):
            self.assertTrue(gateway.business_preview(self.env.company.id,'account.move','create',0,{'ref':'Forbidden'},'')['rejected'])

    def test_forbidden_state_change_and_unknown_action_are_rejected(self):
        partner=self.env['res.partner'].create({'name':'Explicit company contact','company_id':self.env.company.id})
        self.assertTrue(self.gateway.business_preview(self.env.company.id,'res.partner','update',partner.id,{'state':'done'},'')['rejected'])
        self.assertTrue(self.gateway.business_preview(self.env.company.id,'res.partner','action',partner.id,{},'sudo')['rejected'])

    def test_shared_record_is_explicit_in_the_reviewed_scope(self):
        partner=self.env['res.partner'].create({'name':'Shared contact','company_id':False})
        result=self.gateway.business_preview(self.env.company.id,'res.partner','update',partner.id,{'name':'New'},'')
        self.assertIn('REGISTRO COMPARTIDO',result['preview']['notice'])
        self.assertEqual(partner.name,'Shared contact')
