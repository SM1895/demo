# -*- coding: utf-8 -*-



{
    "name": "Colombia - Tax Extended",
    "category": "Localization",
    "version": "16.0.0",
    "author": "Diego Fernando Castaño",
    "website": "https://odoo.com",
    'license': 'OPL-1',
    "summary": "Módulo con funcionalidades extendidas relacionadas a impuestos de la localización Odoo Enterprise - Colombia",

    "depends": ["l10n_co_partner", "purchase", "sale", "l10n_co_edi"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_tax_hierarchy_views.xml",
        "views/account_tax_views.xml"
    ],
    "installable": True,
}
