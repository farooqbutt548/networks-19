# Watilio Integration — Odoo 19

On posting a customer invoice, the invoice PDF is rendered and sent to the customer's
phone on WhatsApp through the Watilio API.

- Contact toggle: **Send WhatsApp Invoice** (default ON). OFF = no PDF/message for that customer.
- Phone taken from the contact's Phone field, normalised to `923001234567`
  (03001234567, +92 300 1234567, 0092..., 3001234567 all work).
- Sent immediately inside action_post (Confirm button); a Watilio error never blocks posting.
- Result on the invoice: WhatsApp tab + chatter entry with the PDF; "Send on WhatsApp" button to resend.
- Configure: Accounting > Settings > WhatsApp Invoice (Watilio).
- Settings: API Secret + WhatsApp Account Unique ID. Endpoint defaults to https://app.watilio.com/api/send/whatsapp
- The invoice PDF is rendered on Post and uploaded directly in the request (document_file); Watilio never downloads it from Odoo.
