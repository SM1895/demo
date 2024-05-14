from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountTaxRetentionIcaAccount(models.Model):
    _name = 'account.tax.retention.ica.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Configuración Asiento ICA y RTEICA'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string='Nombre',
    )
    partner_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta del Tercero',
        tracking=True
    )
    payable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta por Pagar a la Ciudad',
        tracking=True
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
        tracking=True
    )
