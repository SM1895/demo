from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountTaxSettlementIca(models.Model):
    _name = 'account.tax.settlement.ica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Configuración Liquidación ICA'

    total_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingreso Total',
        relation='total_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]"
    )
    return_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingresos por Devoluciones, Rebajas y Descuentos',
        relation='return_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    export_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingresos por Exportaciones',
        relation='export_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    sale_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingresos por Ventas de Activos Fijos',
        relation='sale_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    exclude_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingresos no Sujetos o Excluidos',
        relation='exclude_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    exempt_income_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Ingresos Exentos en este Municipio',
        relation='exempt_income_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    retencion_ica_accounts_ids = fields.Many2many(
        comodel_name='account.account',
        string='Autorretención de ICA',
        relation='retencion_ica_settlement_account_rel',
        column1='settlement_id',
        column2='account_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        other_register = self.search([
            ('company_id', '=', self.env.company.id)
        ])
        if other_register:
            raise ValidationError(
                'No se puede crear más de un registro de Configuración Liquidación ICA.')
        return super().create(vals_list)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(
            'No se puede duplicar un registro de Configuración Liquidación ICA.')
        default = dict(default or {})
        return super().copy(default=default)

    def name_get(self):
        res = []
        for record in self:
            name = 'Configuración Liquidación ICA ' + str(record.id)
            res += [(record.id, name)]
        return res
