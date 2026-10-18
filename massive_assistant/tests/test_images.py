"""Acceptance test: only an explicit image-library confirmation publishes bytes."""
import base64
import io
import unittest
from odoo import release
from odoo.tests.common import TransactionCase


class WebsiteImageTests(TransactionCase):
    def test_reviewed_image_is_specific_to_selected_website(self):
        if release.version_info[0]!=19 or 'website' not in self.env:raise unittest.SkipTest('Requires Odoo 19 Website.')
        from PIL import Image
        website=self.env['website'].search([('company_id','=',self.env.company.id)],limit=1)
        if not website:raise unittest.SkipTest('Requires a website in the test company.')
        data=io.BytesIO();Image.new('RGB',(40,40),'white').save(data,format='JPEG')
        result=self.env['massive.assistant.gateway'].website_image_create(self.env.company.id,website.id,'Reviewed test image',base64.b64encode(data.getvalue()).decode(),'https://source.example/image')
        self.assertTrue(result['complete'])
        attachment=self.env['ir.attachment'].browse(result['id'])
        self.assertTrue(attachment.public);self.assertEqual(attachment.website_id,website)
        self.assertEqual(attachment.company_id,self.env.company)
