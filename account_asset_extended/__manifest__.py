# -*- coding: utf-8 -*-


{
    'name': "Account Asset Extended",

    'summary': """
        Extended module for account asset 
    """,

    'description': """
        Extended module for account asset
    """,

    "author": "Diego Castaño",
    "website": "https://odoo.com.co",
    'license': 'OPL-1',
    'category': 'Purchase',
    'version': '16.0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_asset','product'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/account_asset_views.xml',
        'wizards/asset_modify_views.xml',
    ],
}
