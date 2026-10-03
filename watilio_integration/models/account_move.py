import json
import logging
import re

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_amount, format_date

_logger = logging.getLogger(__name__)

PARAM = 'watilio_integration.'
TIMEOUT = 30


class _SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


class AccountMove(models.Model):
    _inherit = 'account.move'

    whatsapp_state = fields.Selection(
        [('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        string='WhatsApp Status', copy=False, readonly=True)
    whatsapp_sent_date = fields.Datetime(string='WhatsApp Sent On', copy=False, readonly=True)
    whatsapp_phone = fields.Char(string='WhatsApp Number', copy=False, readonly=True)
    whatsapp_error = fields.Text(string='WhatsApp Response', copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Hook: send right after the invoice is confirmed
    # ------------------------------------------------------------------
    def action_post(self):
        res = super().action_post()
        if self._watilio_get('enabled'):
            for move in self.filtered(lambda m: m.state == 'posted' and m.move_type == 'out_invoice'):
                reason = move._watilio_skip_reason()
                if reason:
                    move.write({'whatsapp_state': 'skipped', 'whatsapp_error': reason})
                else:
                    move._watilio_send()
        return res

    # ------------------------------------------------------------------
    # Button: manual (re)send
    # ------------------------------------------------------------------
    def action_watilio_send(self):
        for move in self:
            if move.state != 'posted' or move.move_type != 'out_invoice':
                raise UserError(_('Only posted customer invoices can be sent on WhatsApp.'))
            reason = move._watilio_skip_reason(manual=True)
            if reason:
                raise UserError(reason)
            move._watilio_send()
        failed = self.filtered(lambda m: m.whatsapp_state == 'failed')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('WhatsApp'),
                'message': _('Sending failed: %s', failed[:1].whatsapp_error) if failed
                else _('Invoice sent on WhatsApp.'),
                'type': 'danger' if failed else 'success',
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _watilio_get(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM + key, default) or default

    def _watilio_partner_phone(self):
        self.ensure_one()
        for partner in (self.partner_id, self.partner_id.commercial_partner_id):
            number = partner.phone or (partner.mobile if 'mobile' in partner._fields else False)
            if number:
                return number
        return False

    def _watilio_skip_reason(self, manual=False):
        self.ensure_one()
        partner = self.partner_id
        if not manual:
            if not partner.whatsapp_invoice_enabled or not partner.commercial_partner_id.whatsapp_invoice_enabled:
                return _('"Send WhatsApp Invoice" is turned off on the customer.')
        if not self._watilio_get('secret') or not self._watilio_get('account'):
            return _('Watilio API Secret / WhatsApp Account ID is not configured in Settings.')
        if not self._watilio_normalize_phone(self._watilio_partner_phone()):
            return _('Customer has no valid phone number.')
        return False

    def _watilio_normalize_phone(self, raw):
        """Return number as 923001234567 (digits only, country code, no +)."""
        cc = re.sub(r'\D', '', self._watilio_get('country_code', '92')) or '92'
        digits = re.sub(r'\D', '', raw or '')
        if digits.startswith('00'):
            digits = digits[2:]
        if digits.startswith(cc):
            pass
        elif digits.startswith('0'):
            digits = cc + digits[1:]
        elif len(digits) == 10:
            digits = cc + digits
        return digits if 10 <= len(digits) <= 15 else False

    def _watilio_caption(self):
        self.ensure_one()
        template = self._watilio_get('message_template') or 'Invoice {number}'
        values = _SafeDict(
            customer=self.partner_id.name or '',
            number=self.name or '',
            amount=format_amount(self.env, self.amount_total, self.currency_id),
            date=format_date(self.env, self.invoice_date) if self.invoice_date else '',
            due_date=format_date(self.env, self.invoice_date_due) if self.invoice_date_due else '',
            company=self.company_id.name or '',
        )
        return template.format_map(values)

    def _watilio_pdf_attachment(self):
        """Render the invoice PDF and store it as an attachment on the invoice."""
        self.ensure_one()
        pdf, _type = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'account.account_invoices', res_ids=self.ids)
        if hasattr(self, '_get_invoice_report_filename'):
            filename = self._get_invoice_report_filename()
        else:
            filename = '%s.pdf' % (self.name or 'Invoice').replace('/', '_')
        return self.env['ir.attachment'].sudo().create({
            'name': filename,
            'raw': pdf,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': self.id,
        })

    def _watilio_send(self):
        self.ensure_one()
        phone = self._watilio_normalize_phone(self._watilio_partner_phone())
        try:
            attachment = self._watilio_pdf_attachment()
            response_text = self._watilio_request(phone, self._watilio_caption(), attachment)
        except Exception as e:  # noqa: BLE001 - never block invoicing
            _logger.exception('Watilio send failed for %s', self.name)
            self.write({'whatsapp_state': 'failed', 'whatsapp_phone': phone, 'whatsapp_error': str(e)[:2000]})
            self.message_post(body=_('WhatsApp invoice to %(phone)s failed: %(err)s', phone=phone, err=str(e)[:500]))
            return False

        self.write({
            'whatsapp_state': 'sent',
            'whatsapp_phone': phone,
            'whatsapp_sent_date': fields.Datetime.now(),
            'whatsapp_error': response_text[:2000],
        })
        self.message_post(
            body=_('Invoice sent on WhatsApp to %s.', phone),
            attachment_ids=attachment.ids,
        )
        return True

    def _watilio_request(self, phone, caption, attachment):
        """POST to Watilio as multipart form data with the invoice PDF attached."""
        get = self._watilio_get
        url = get('api_url', 'https://app.watilio.com/api/send/whatsapp')
        try:
            data = json.loads(get('extra_params') or '{}')
        except ValueError:
            raise UserError(_('"Extra Parameters" in Settings is not valid JSON.'))

        data.update({
            'secret': get('secret'),
            'account': get('account'),
            'recipient': phone,
            'type': 'document',
            'message': caption,
            'document_name': attachment.name,
            'document_type': 'pdf',
        })
        # Send the rendered PDF itself in the request (no public link needed)
        files = {'document_file': (attachment.name, attachment.raw, 'application/pdf')}

        resp = requests.post(url, data=data, files=files, timeout=TIMEOUT)
        text = resp.text or ''
        try:
            body = resp.json()
        except ValueError:
            body = None
        status = body.get('status') if isinstance(body, dict) else None
        if not resp.ok or str(status) != '200':
            msg = body.get('message') if isinstance(body, dict) else text[:500]
            raise UserError(_('Watilio error (HTTP %(code)s): %(msg)s', code=resp.status_code, msg=msg))
        return text
