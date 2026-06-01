from odoo import models, api
from datetime import date, datetime, timedelta
import requests


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def call_auto_rate_sync(self, company_id):
        company = self.browse(company_id)
        company.currency_id.update_auto_exchange_rates(company)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def update_auto_exchange_rates(self, company_rec):
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('auto_currency_rate.api_key')
        base_api_url = params.get_param(
            'auto_currency_rate.api_base_url',
            default="https://v6.exchangerate-api.com/v6"
        )

        currencies = self.search([('active', '=', True)])
        company = company_rec if company_rec else self.env.company

        for currency in currencies:
            if company.currency_id != currency:
                if not api_key or not base_api_url:
                    return

                url = f"{base_api_url}/{api_key}/latest/{company.currency_id.name}"
                response = requests.get(url)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('result') == 'success':
                        rates = data.get('conversion_rates', {})
                        curr_rate = rates.get(currency.name)

                        if curr_rate is not None:
                            rate_vals = {
                                'name': date.today(),
                                'company_id': company.id,
                                'company_rate': curr_rate
                            }

                            existing_rate = self.env['res.currency.rate'].search([
                                ('currency_id', '=', currency.id),
                                ('company_id', '=', company.id),
                                ('name', '=', date.today())
                            ], limit=1)

                            if existing_rate:
                                existing_rate.sudo().write({
                                    'company_rate': curr_rate
                                })
                            else:
                                currency.sudo().write({
                                    'rate_ids': [(0, 0, rate_vals)]
                                })