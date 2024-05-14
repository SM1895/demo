from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    apply_retention_income_tax = fields.Boolean(
        string='Aplica para Retención de ICA por Ingresos'
    )
