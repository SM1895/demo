import logging
from odoo import fields, models, _
from io import BytesIO


class AccountConceptAccountWizard(models.TransientModel):
    _name = 'account.concept.account.wizard'

    account_exogenus_format_concept_id = fields.Many2one(
        'account.exogenus.formats.concepts', string="Exogenus Format Column")
    account_exogenus_concept_account_ids = fields.Many2many(
        'account.account',
        string='Accounts')

    def button_select_accounts(self):
        res = []
        for account in self.account_exogenus_concept_account_ids:
            res.append((0, 0, {'account_id': account.id}))
        print("***button_select_accounts****", res,
              self.account_exogenus_format_concept_id)
        self.account_exogenus_format_concept_id.concept_exogenus_account_ids = (
            res)
