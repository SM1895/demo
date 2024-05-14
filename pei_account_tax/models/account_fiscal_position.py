from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_retention = fields.Boolean(
        string='Incluir en Proceso de Retención de ICA'
    )
