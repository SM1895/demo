from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountTaxApportionment(models.Model):
    _name = 'account.tax.apportionment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Prorrateo de IVA'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string='Nombre',
        tracking=True
    )
    income_categories_ids = fields.Many2many(
        comodel_name='account.tax.apportionment.group',
        relation='apportionment_income_rel',
        column1='apportionment_id',
        column2='apportionment_group_id',
        string='Categorías de Ingreso',
        tracking=True
    )
    iva_categories_ids = fields.Many2many(
        comodel_name='account.tax.apportionment.iva',
        relation='apportionment_iva_rel',
        column1='apportionment_id',
        column2='apportionment_iva_id',
        string='Categorías IVA',
        tracking=True
    )
    account_setting_id = fields.Many2one(
        comodel_name='account.tax.apportionment.account',
        string='Configuración Contable',
        tracking=True
    )
    iva_line_ids = fields.One2many(
        comodel_name='account.tax.apportionment.line',
        inverse_name='apportionment_id',
        domain=[('apportionment_type', '=', 'iva')],
        string='Lineas de IVA',
        tracking=True
    )
    group_line_ids = fields.One2many(
        comodel_name='account.tax.apportionment.line',
        inverse_name='apportionment_id',
        domain=[('apportionment_type', '=', 'income')],
        string='Lineas de Ingresos',
        tracking=True
    )
    date_from = fields.Date(
        string='Fecha Inicial',
        tracking=True
    )
    date_to = fields.Date(
        string='Fecha Final',
        tracking=True
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Asiento Contable',
        tracking=True
    )
    is_main_company = fields.Boolean(
        string='Es PEI'
    )
    account_analytics_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        relation='apportionment_account_analytic_rel',
        column1='apportionment_id',
        column2='account_id',
        string='Cuentas Analíticas',
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError(
                    'La fecha inicial debe ser inferior a la final.')
    
    def clean_lines(self):
        for record in self:
            record.group_line_ids.unlink()
            record.iva_line_ids.unlink()
    
    def _create_group_lines(self):
        for record in self:
            total_moves_groups = 0
            for group_id in record.income_categories_ids:
                line_group = self.env['account.tax.apportionment.line'].search([
                    ('apportionment_group_id', '=', group_id.id),
                    ('apportionment_type', '=', 'income'),
                    ('apportionment_id', '=', record.id)
                ])
                if line_group:
                    total_amount = sum([x.debit - x.credit for x in line_group.detail_ids.filtered(
                        lambda x: x.not_in_balance is False)])
                    line_group.amount_moves = total_amount
                    if line_group.apportionment_group_id.exclude_from_compute:
                        total_amount = 0
                else:
                    moves = self.env['account.move.line'].search([
                        ('move_id.state', '=', 'posted'),
                        ('account_id', 'in', group_id.accounts_ids.ids),
                        ('date', '>=', record.date_from),
                        ('date', '<=', record.date_to)
                    ])
                    if record.account_analytics_ids and record.is_main_company:
                        moves_list = self.env['account.move.line']
                        for move in moves:
                            if isinstance(move.analytic_distribution, dict):
                                keys = move.analytic_distribution.keys()
                                for key in keys:
                                    if int(key) in record.account_analytics_ids.ids and move not in moves_list:
                                        moves_list += move
                    else:
                        moves_list = moves
                    total_amount = sum([x.debit - x.credit for x in moves_list])
                    line_group = self.env['account.tax.apportionment.line'].create({
                        'amount_moves': total_amount,
                        'apportionment_type': 'income',
                        'apportionment_group_id': group_id.id,
                        'apportionment_id': record.id
                    })
                    if group_id.exclude_from_compute:
                        total_amount = 0
                    for move in moves_list:
                        self.env['account.tax.apportionment.detail'].create({
                            'move_line_id': move.id,
                            'line_id': line_group.id
                        })
                total_moves_groups += total_amount
            if total_moves_groups != 0:
                for line in record.group_line_ids.filtered(
                        lambda x: x.apportionment_group_id.exclude_from_compute is False):
                    line.percentage = ((line.amount_moves * 100) / total_moves_groups) / 100

    def _create_iva_lines(self):
        for record in self:
            total_moves_groups = 0
            for group_id in record.iva_categories_ids:
                line_group = self.env['account.tax.apportionment.line'].search([
                    ('apportionment_iva_id', '=', group_id.id),
                    ('apportionment_type', '=', 'iva'),
                    ('apportionment_id', '=', record.id)
                ])
                if line_group:
                    total_amount = sum([x.debit - x.credit for x in line_group.detail_ids.filtered(
                        lambda x: x.not_in_balance is False)])
                    line_group.amount_moves = total_amount
                else:
                    moves = self.env['account.move.line'].search([
                        ('move_id.state', '=', 'posted'),
                        ('account_id', 'in', group_id.accounts_ids.ids),
                        ('date', '>=', record.date_from),
                        ('date', '<=', record.date_to)
                    ])
                    if record.account_analytics_ids and record.is_main_company:
                        moves_list = self.env['account.move.line']
                        for move in moves:
                            if isinstance(move.analytic_distribution, dict):
                                keys = move.analytic_distribution.keys()
                                for key in keys:
                                    if int(key) in record.account_analytics_ids.ids:
                                        moves_list += move
                    else:
                        moves_list = moves
                    total_amount = sum([x.debit - x.credit for x in moves_list])
                    line_group = self.env['account.tax.apportionment.line'].create({
                        'amount_moves': total_amount,
                        'apportionment_type': 'iva',
                        'apportionment_iva_id': group_id.id,
                        'apportionment_id': record.id
                    })
                    for move in moves_list:
                        self.env['account.tax.apportionment.detail'].create({
                            'move_line_id': move.id,
                            'line_id': line_group.id
                        })
                if group_id.is_discountable:
                    lines = self.group_line_ids.filtered(
                        lambda x: x.apportionment_group_id.id == group_id.group_id.id)
                    percentage = sum([x.percentage for x in lines])
                    line_group.amount_reject_iva = line_group.amount_moves * percentage
                total_moves_groups += total_amount

    def compute_line_values(self):
        for record in self:
            record._create_group_lines()
            record._create_iva_lines()

    def create_account_move(self):
        for record in self:
            if record.move_id:
                raise ValidationError('Este registro tiene un asiento contable creado y asociado.')
            if record.is_main_company:
                other_apportionment = self.search([
                    ('is_main_company', '=', True),
                    ('move_id', '!=', False),
                    ('account_analytics_ids', '=', record.account_analytics_ids.ids)
                ])
                for apportionment in other_apportionment:
                    if apportionment.account_analytics_ids.ids == record.account_analytics_ids.ids:
                        if (apportionment.move_id.date >= record.date_from
                                and apportionment.move_id.date <= record.date_to):
                            raise ValidationError(
                                'Ya existe un asiento contable para el rango de fechas y cuentas analiticas seleccionadas.')
            amount_reject_iva = abs(sum(
                [x.amount_reject_iva for x in self.iva_line_ids]))
            if amount_reject_iva == 0:
                raise ValidationError(
                    'El valor de iva rechazado debe ser superior a cero.')
            analytic_distribution = record._get_analytic_distribution()
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': record.account_setting_id.journal_id.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': record.account_setting_id.account_tax_id.id,
                        'credit': amount_reject_iva,
                        'analytic_distribution': analytic_distribution}
                    ),
                    (0, 0, {
                        'account_id': record.account_setting_id.expense_account_id.id,
                        'debit': amount_reject_iva,
                        'analytic_distribution': analytic_distribution}
                    ),
                ]
            }
            move = self.env['account.move'].create(move_vals)
            record.move_id = move

    def unlink(self):
        for record in self:
            if record.move_id:
                raise ValidationError(
                    'Este registro no puede ser eliminado, debido a que se ha realizado un movimiento contable.')
            record.clean_lines()
        return super().unlink()

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'account.tax.apportionment' or self._name == 'account.tax.apportionment':
            if self.env.company.name == 'Patrimonio Autónomo Estrategias Inmobiliarias PEI':
                defaults.update(
                    is_main_company=True
                )
        return defaults

    def _get_analytic_distribution(self):
        analytic_distribution = {}
        if self.is_main_company:
            for analytic in self.account_analytics_ids:
                analytic_distribution[str(analytic.id)] = 100
        return analytic_distribution
