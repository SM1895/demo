from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountTaxApportionmentDetail(models.Model):
    _name = 'account.tax.apportionment.detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Prorrateo de IVA Detalle'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True
    )
    move_line_id = fields.Many2one(
        string='Movimiento Contable',
        comodel_name='account.move.line',
    )
    date = fields.Date(
        string='Fecha de Radicación',
        related='move_line_id.date'
    )
    move_id = fields.Many2one(
        string='Asiento Contable',
        comodel_name='account.move',
        related='move_line_id.move_id'
    )
    account_id = fields.Many2one(
        string='Cuenta',
        comodel_name='account.account',
        related='move_line_id.account_id'
    )
    partner_id = fields.Many2one(
        string='Asociado',
        comodel_name='res.partner',
        related='move_line_id.partner_id'
    )
    debit = fields.Monetary(
        string='Débito',
        currency_field='company_currency_id',
        related='move_line_id.debit'
    )
    credit = fields.Monetary(
        string='Crédito',
        currency_field='company_currency_id',
        related='move_line_id.credit'
    )
    not_in_balance = fields.Boolean(
        string='Excluir del Balance',
    )
    line_id = fields.Many2one(
        comodel_name='account.tax.apportionment.line',
        string='Línea',
    )
    income_id = fields.Many2one(
        comodel_name='account.tax.retention.income',
        string='Ingreso',
    )
    analytic_distribution = fields.Json(
        string="Analítico",
        related='move_line_id.analytic_distribution'
    )
    analytic_distribution_search = fields.Json(
        store=False
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get(
            "Percentage Analytic"),
    )
