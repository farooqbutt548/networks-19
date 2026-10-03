from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_invoice_enabled = fields.Boolean(
        string='Send WhatsApp Invoice',
        default=True,
        help='When enabled, posted customer invoices are sent to this contact on WhatsApp (via Watilio).',
    )
