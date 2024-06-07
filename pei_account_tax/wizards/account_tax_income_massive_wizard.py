from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountTaxIncomeMassiveWizard(models.TransientModel):
    _name = 'account.tax.income.massive.wizard'
    _description = 'Configuración Masiva de Cuentas'

    account_ids = fields.Many2many(
        relation="massive_account_rel",
        comodel_name='account.account',
        string='Cuentas Contables',
        domain="[('id', 'not in', domain_account_ids),('apply_retention_income_tax', '=', True)]"
    )
    domain_account_ids = fields.Many2many(
        relation="domain_massive_account_rel",
        comodel_name='account.account',
        string='Dominio Cuentas Contables',
    )
    retention_id = fields.Many2one(
        comodel_name='account.tax.retention.ica',
        string='Retención'
    )

    def add_accounts(self):
        for account in self.account_ids:
            self.env['account.tax.retention.income'].create({
                'retention_id': self.retention_id.id,
                'account_id': account.id
            })
