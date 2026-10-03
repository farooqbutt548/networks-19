from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    watilio_enabled = fields.Boolean(
        string='Send Invoices on WhatsApp', config_parameter='watilio_integration.enabled')
    watilio_api_url = fields.Char(
        string='Send Endpoint', config_parameter='watilio_integration.api_url',
        default='https://app.watilio.com/api/send/whatsapp')
    watilio_secret = fields.Char(
        string='API Secret', config_parameter='watilio_integration.secret',
        help='Watilio dashboard > Tools > API Keys.')
    watilio_account = fields.Char(
        string='WhatsApp Account Unique ID', config_parameter='watilio_integration.account',
        help='Unique ID of the linked WhatsApp account (Watilio dashboard > WhatsApp > Accounts).')
    watilio_extra_params = fields.Char(
        string='Extra Parameters (JSON)', config_parameter='watilio_integration.extra_params',
        help='Optional extra Watilio fields, e.g. {"priority": 1}')
    watilio_country_code = fields.Char(
        string='Default Country Code', config_parameter='watilio_integration.country_code', default='92')
    watilio_message_template = fields.Char(
        string='Message Text', config_parameter='watilio_integration.message_template',
        default='Dear {customer}, please find attached invoice {number} of {amount} dated {date}. '
                'Due date: {due_date}. Thank you, {company}.',
        help='Placeholders: {customer} {number} {amount} {date} {due_date} {company}')
