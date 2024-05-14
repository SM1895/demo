# -*- coding: utf-8 -*-
 

{
    'name': "Account Tax",
    'summary': """
        Contiene la información y configuraciones necesarias para los procesos de impuestos""",
    'description': """
        Contiene la información y configuraciones necesarias para los procesos de impuestos""",
    'contributors': [
        'Diego Fernando Castaño, diegoferledesma@gmail.com'
    ],
    'website': "http://www.odoo.com.co",
    'version': '16.0.0.0.0',
    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'account_accountant',
        'l10n_co_reports',
        'account_reports',
        'l10n_co_tax',
        "l10n_co_partner",
        'base_address_extended',
        'pei_account_analytic',
        'pei_financial',
        'purchase',
    ],
    # always loaded
    'data': [
        'security/account_tax_security.xml',
        'security/ir.model.access.csv',
        'views/account_tax_menus.xml',
        'views/account_tax_view.xml',
        'views/account_tax_retention_table_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/account_tax_hierarchy_view.xml',
        'views/account_tax_apportionment_group_view.xml',
        'views/account_tax_apportionment_iva_view.xml',
        'views/account_tax_apportionment_account_view.xml',
        'views/account_tax_apportionment_view.xml',
        'views/account_tax_apportionment_line_view.xml',
        'views/account_account_view.xml',
        'views/account_tax_retention_ica_view.xml',
        'views/account_tax_retention_income_view.xml',
        'views/account_tax_retention_ica_group_view.xml',
        'views/account_tax_retention_ica_account_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/res_config_settings_view.xml',
        'views/account_tax_aiu.xml',
        'views/purchase_order_view.xml',
        'views/account_tax_settlement_ica_view.xml',
        'views/account_tax_settlement_ica_taxable_view.xml',
        'wizards/account_tax_income_massive_wizard_view.xml',
    ],
    'auto_install': True,
    "installable": True,
    "license": "AGPL-3",
    "application": True,
}