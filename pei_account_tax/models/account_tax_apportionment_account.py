from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountTaxApportionmentAccount(models.Model):
    _name = 'account.tax.apportionment.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Configuración Asiento Contable Prorrateo'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string='Nombre',
    )
    account_tax_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta de IVA Descontable',
        tracking=True
    )
    expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta del Gasto x Prorrateo',
        tracking=True
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario de Prorrateo',
        tracking=True
    )

    @api.constrains('account_tax_id', 'expense_account_id')
    def _check_accounts(self):
        for record in self:
            if record.account_tax_id.id == record.expense_account_id.id:
                raise ValidationError(
                    'No se pueden configurar las mismas cuenta para este registro.')
