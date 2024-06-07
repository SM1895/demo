import logging
from odoo import fields, models, _
from io import BytesIO


class AccountColumnAccountWizard(models.TransientModel):
    _name = 'account.column.account.wizard'

    account_exogenus_format_column_id = fields.Many2one(
        'account.exogenus.formats.columns', string="Exogenus Format Column")
    acount_exogenus_column_account_ids = fields.Many2many(
        'account.account',
        string='Accounts')

    def button_select_accounts(self):
        res = []
        for account in self.acount_exogenus_column_account_ids:
            res.append((0, 0, {'account_id': account.id}))
        self.account_exogenus_format_column_id.account_colums_ids = res
