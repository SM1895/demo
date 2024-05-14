# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountTaxRetentionIncome(models.Model):
    _name = 'account.tax.retention.income'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta',
        tracking=True
    )
    ciiu_id = fields.Many2one(
        comodel_name='ciiu.value',
        string='Código CIIU',
        tracking=True
    )
    fee_value = fields.Float(
        string='Tarifa',
        compute='_compute_fee_value',
        store=True,
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        compute='_compute_tax_id',
        string='Impuesto',
        store=True,
    )
    amount_move = fields.Monetary(
        string='Movimiento',
        currency_field='company_currency_id',
        compute='_compute_amount_move',
        store=True,
        tracking=True
    )
    amount_balance = fields.Monetary(
        string='Saldo',
        currency_field='company_currency_id',
        compute='_compute_amount_balance',
        store=True,
        tracking=True
    )
    amount_retention = fields.Monetary(
        string='Retención Calculada',
        currency_field='company_currency_id',
        compute='_compute_amount_retention',
        store=True,
        tracking=True
    )
    retention_id = fields.Many2one(
        comodel_name='account.tax.retention.ica',
        string='Retención',
    )
    detail_ids = fields.One2many(
        comodel_name='account.tax.apportionment.detail',
        inverse_name='income_id',
        string='Detalles'
    ) 
    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True
    )
    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Cuentas Analíticas'
    )

    @api.constrains('account_id')
    def _check_account_id(self):
        for record in self:
            if not record.account_id:
                continue
            other_detail = self.search([
                ('account_id', '=', record.account_id.id),
                ('retention_id', '=', record.retention_id.id),
                ('id', '!=', record.id)
            ])
            if other_detail:
                raise ValidationError(
                    'Ya se ha agregado una línea con la cuenta seleccionada.')

    def update_details(self):
        for record in self:
            if record.analytic_account_ids:
                moves_list = self.env['account.move.line']
                for move in record.detail_ids:
                    if isinstance(move.move_line_id.analytic_distribution, dict):
                        keys = move.move_line_id.analytic_distribution.keys()
                        for key in keys:
                            if int(key) in record.analytic_account_ids.ids and move.move_line_id not in moves_list:
                                moves_list += move.move_line_id
                details = record.detail_ids.filtered(
                    lambda x: x.move_line_id.id not in moves_list.ids)
                details.unlink()

    @api.depends('retention_id.city_id', 'ciiu_id')
    def _compute_fee_value(self):
        for record in self:
            ica = self.env['account.tax.retention.table'].search([
                ('ciiu_activity_id', '=', record.ciiu_id.id),
                ('city_id', '=', record.retention_id.city_id.id),
                ('company_id', '=', record.company_id.id)
            ], limit=1)
            if ica:
                record.fee_value = ica.fee_retention / 100
            else:
                record.fee_value = 0

    @api.depends('retention_id.city_id', 'ciiu_id')
    def _compute_tax_id(self):
        for record in self:
            ica = self.env['account.tax.retention.table'].search([
                ('ciiu_activity_id', '=', record.ciiu_id.id),
                ('city_id', '=', record.retention_id.city_id.id),
                ('company_id', '=', record.company_id.id)
            ], limit=1)
            if ica:
                record.tax_id = ica.rteica_tax_id

    @api.depends('account_id', 'retention_id.date_from', 'retention_id.date_to')
    def _compute_amount_balance(self):
        for record in self:
            moves = self.env['account.move.line'].search([
                ('move_id.state', '=', 'posted'),
                ('account_id', '=', record.account_id.id),
            ])
            record.amount_balance = sum([x.debit - x.credit for x in moves])

    @api.depends('amount_move', 'fee_value', 'retention_id.min_base_retention')
    def _compute_amount_retention(self):
        for record in self:
            amount_retention = record.amount_move * record.fee_value
            if abs(amount_retention) > record.retention_id.min_base_retention:
                record.amount_retention = amount_retention
            else:
                record.amount_retention = 0

    @api.depends('detail_ids')
    def _compute_amount_move(self):
        for record in self:
            record.amount_move = sum(
                [x.debit - x.credit for x in record.detail_ids.filtered(
                    lambda x: x.not_in_balance is False)])

    def _create_detail_lines(self):
        for record in self:
            record.detail_ids.unlink()
            moves = self.env['account.move.line'].search([
                ('move_id.state', '=', 'posted'),
                ('account_id', '=', record.account_id.id),
                ('date', '>=', record.retention_id.date_from),
                ('date', '<=', record.retention_id.date_to)
            ])
            for move in moves:
                self.env['account.tax.apportionment.detail'].create({
                    'move_line_id': move.id,
                    'income_id': record.id
                })
            record.update_details()

    def action_view_audit(self):
        self.ensure_one()
        return {
            'name': self.account_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.tax.retention.income',
            'res_id': self.id,
        }

    def clean_lines(self):
        for record in self:
            record.detail_ids.unlink()
