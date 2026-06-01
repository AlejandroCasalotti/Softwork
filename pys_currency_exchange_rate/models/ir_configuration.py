from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    exchange_rate_api_key = fields.Char(string="Auto Exchange Rate API Key")
    base_currency = fields.Many2one('res.currency', string="Base Currency")
    api_base_url = fields.Char(
        string="Currency Rate API Base URL",
        default="https://v6.exchangerate-api.com/v6"
    )

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('auto_currency_rate.api_key', self.exchange_rate_api_key)
        params.set_param('auto_currency_rate.base_currency', self.base_currency.id)
        params.set_param('auto_currency_rate.api_base_url', self.api_base_url)

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()

        res['exchange_rate_api_key'] = params.get_param('auto_currency_rate.api_key')
        res['api_base_url'] = params.get_param(
            'auto_currency_rate.api_base_url',
            default="https://v6.exchangerate-api.com/v6"
        )

        base_currency_id = int(
            params.get_param('auto_currency_rate.base_currency', default=0)
        )
        res['base_currency'] = base_currency_id if base_currency_id else False
        return res
