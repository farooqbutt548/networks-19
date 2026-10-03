{
    'name': 'Watilio Integration',
    'version': '19.0.1.3.0',
    'summary': 'Send the invoice PDF to the customer on WhatsApp via Watilio when an invoice is posted',
    'author': 'Prime System Solutions',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
