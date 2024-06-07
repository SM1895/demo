from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date

LIST_DETAILS = [
    'total_income',
    'out_total_income',
    'total_income_city',
    'return_total_income',
    'export_total_income',
    'sale_total_income',
    'exclude_total_income',
    'exempt_total_income',
    'taxable_total_income',
    'tax_total_income',
    'retention_total_income',
    'total_positive_balance',
    'tax_charge_total_income',
    'tax_advice_total_income',
    'tax_charge_advice_total_income',
    'surcharge_total_income',
    'tax_surcharge_total_income',
    'discount_total_income',
    'net_tax_total_income',
]

class AccountTaxSettlementIcaTaxable(models.Model):
    _name = 'account.tax.settlement.ica.taxable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Liquidación ICA'

    @api.model
    def _get_year_selection(self):
        year_list = []
        current_date = datetime.now().year
        start_date = current_date - 5
        end_date = current_date + 5
        year_list = [(str(year), str(year)) for year in range(start_date, end_date + 1)]
        return year_list

    name = fields.Char(
        string='Nombre',
    )
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Ciudad'
    )
    surcharge = fields.Float(
        string='Sobretasa Bomberil'
    )
    discount = fields.Float(
        string='Descuento por Pronto Pago'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('in_execution', 'En Ejecución'),
            ('validated', 'Validado'),
            ('canceled', 'Cancelado')
        ],
        string='Estado',
        default='draft',
        tracking=True
    )
    date_selection = fields.Selection(
        _get_year_selection,
        string="Año",
        required=True,
        unique=True
    )
    line_ids = fields.One2many(
        comodel_name='account.tax.settlement.ica.taxable.line',
        string='Detalles',
        inverse_name='settlement_id'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    @api.constrains('surcharge')
    def _check_surcharge(self):
        for record in self:
            if record.surcharge < 0:
                raise ValidationError(
                    'La Sobretasa Bomberi no puede ser negativa.')

    @api.constrains('discount')
    def _check_discount(self):
        for record in self:
            if record.discount < 0:
                raise ValidationError(
                    'El Descuento por Pronto Pago no puede ser negativo.')

    @api.constrains('city_id', 'date_selection')
    def _check_unique(self):
        for record in self:
            other_register = self.search([
                ('city_id', '=', record.city_id.id),
                ('date_selection', '=', record.date_selection),
                ('company_id', '=', self.env.company.id),
                ('id', '!=', record.id)
            ])
            if other_register:
                raise ValidationError(
                    'Ya se encuentra una liquidación de ICA para esta ciudad en este periodo, por favor validar.')

    def action_to_in_execution(self):
        for record in self:
            setting = self.env['account.tax.settlement.ica'].search([
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if not setting:
                raise ValidationError(
                    'No se ha encontrado una de Configuración Liquidación ICA.')
            date_from, date_to = record._get_interval_date(record.date_selection)
            record._compute_line_values(setting, date_from, date_to)
            record.state = 'in_execution'

    def action_to_validated(self):
        for record in self:
            record.state = 'validated'

    def action_to_canceled(self):
        for record in self:
            record.state = 'canceled'

    def action_to_draft(self):
        for record in self:
            record._clean_totals()
            record.state = 'draft'

    @api.model
    def default_get(self, fields_list):
        rslt = super().default_get(fields_list)
        if 'line_ids' in fields_list:
            line_ids = []
            for detail in LIST_DETAILS:
                line_ids.append((0, 0, {
                    'taxable_type': detail
                }))
            rslt['line_ids'] = line_ids
        return rslt

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(
            'No se puede duplicar un registro de Liquidación ICA.')
        default = dict(default or {})
        return super().copy(default=default)

    def _get_interval_date(self, year):
        date_from = date(int(year), 1, 1)
        date_to = date(int(year), 12, 31)
        return date_from, date_to

    def _round_amount(self, value):
        return round(value / 1000) * 1000

    def _compute_line_values(self, setting, date_from, date_to):
        for record in self:
            record._clean_totals()
            record._compute_total_income(setting, date_from, date_to)
            record._compute_total_income_city(setting, date_from, date_to)
            record._compute_out_total_income()
            record._compute_return_total_income(setting, date_from, date_to)
            record._compute_export_total_income(setting, date_from, date_to)
            record._compute_sale_total_income(setting, date_from, date_to)
            record._compute_exclude_total_income(setting, date_from, date_to)
            record._compute_exempt_total_income(setting, date_from, date_to)
            record._compute_taxable_total_income()
            record._compute_tax_total_income()
            record._compute_retention_total_income(setting, date_from, date_to)
            compute_other_lines = record._total_positive_balance_or_tax_charge_total_income()
            if compute_other_lines:
                record._compute_tax_advice_total_income()
                record._compute_tax_charge_advice_total_income()
                record._compute_surcharge_total_income()
                record._compute_tax_surcharge_total_income()
                record._compute_discount_total_income()
                record._compute_net_tax_total_income()

    def _get_filtered_moves(self, accounts, date_from, date_to, analytics=[]):
        moves = self.env['account.move.line'].search([
            ('account_id', 'in', accounts),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        if not analytics:
            return moves
        moves_filtered = self.env['account.move.line']
        for move in moves.filtered(
                lambda x: isinstance(x.analytic_distribution, dict) is True):
            for analytic in analytics:
                if str(analytic) in move.analytic_distribution.keys():
                    moves_filtered += move
                    continue
        return moves_filtered

    def _update_line(self, moves, taxable_type):
        for record in self:
            amount_total = abs(sum([x.debit - x.credit for x in moves]))
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == taxable_type)
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _get_line_value(self, taxable_type):
        return sum(
            [x.amount_move for x in self.line_ids.filtered(
                lambda x: x.taxable_type == taxable_type)])

    def _clean_totals(self):
        for record in self:
            for line in record.line_ids:
                line.write({
                    'amount_move': 0,
                    'amount_move_round': 0
                })

    def _compute_total_income(self, setting, date_from, date_to):
        accounts = setting.total_income_accounts_ids.ids
        for record in self:
            moves = record._get_filtered_moves(accounts, date_from, date_to)
            record._update_line(moves, 'total_income')

    def _compute_total_income_city(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.total_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'total_income_city')

    def _compute_out_total_income(self):
        for record in self:
            total_income = record._get_line_value('total_income')
            total_income_city = record._get_line_value('total_income_city')
            amount_total = total_income - total_income_city
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'out_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_return_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.return_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'return_total_income')

    def _compute_export_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.export_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'export_total_income')

    def _compute_sale_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.sale_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'sale_total_income')

    def _compute_exclude_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.exclude_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'exclude_total_income')

    def _compute_exempt_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.exempt_income_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'exempt_total_income')

    def _compute_taxable_total_income(self):
        for record in self:
            total_income_city = record._get_line_value('total_income_city')
            return_total_income = record._get_line_value('return_total_income')
            export_total_income = record._get_line_value('export_total_income')
            sale_total_income = record._get_line_value('sale_total_income')
            exclude_total_income = record._get_line_value('exclude_total_income')
            exempt_total_income = record._get_line_value('exempt_total_income')
            amount_total = abs(total_income_city
                               - return_total_income
                               - export_total_income
                               - sale_total_income
                               - exclude_total_income
                               - exempt_total_income)
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'taxable_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_tax_total_income(self):
        for record in self:
            percentage = 0
            taxable_total_income = record._get_line_value('taxable_total_income')
            ica_setting = self.env['account.tax.retention.table'].search([
                ('city_id', '=', record.city_id.id)
            ], limit=1)
            if ica_setting:
                percentage = ica_setting.fee_ica
            amount_total = abs(taxable_total_income * (percentage / 100))
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'tax_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_retention_total_income(self, setting, date_from, date_to):
        for record in self:
            city_analitycs = self.env['account.tax.retention.ica.group'].search([
                ('city_id', '=', self.city_id.id)
            ], limit=1)
            accounts = setting.retencion_ica_accounts_ids.ids
            if accounts and city_analitycs:
                moves = record._get_filtered_moves(
                    accounts, date_from, date_to, city_analitycs.account_analytics_ids.ids)
                record._update_line(moves, 'retention_total_income')

    def _total_positive_balance_or_tax_charge_total_income(self):
        compute_other_lines = True
        tax_total_income = self._get_line_value('tax_total_income')
        retention_total_income = self._get_line_value('retention_total_income')
        amount_total = tax_total_income - retention_total_income
        lines = self.line_ids.filtered(
            lambda x: x.taxable_type in (
                'tax_charge_total_income', 'total_positive_balance'))
        for line in lines:
            line.write({
                'amount_move': 0,
                'amount_move_round': 0
            })
        if amount_total > 0:
            lines = self.line_ids.filtered(
                lambda x: x.taxable_type == 'tax_charge_total_income')
            for line in lines:
                line.write({
                    'amount_move': abs(amount_total),
                    'amount_move_round': self._round_amount(abs(amount_total))
                })
        elif amount_total < 0:
            compute_other_lines = False
            lines = self.line_ids.filtered(
                lambda x: x.taxable_type == 'total_positive_balance')
            for line in lines:
                line.write({
                    'amount_move': abs(amount_total),
                    'amount_move_round': self._round_amount(abs(amount_total))
                })
        return compute_other_lines

    def _compute_tax_advice_total_income(self):
        for record in self:
            ica_setting = self.env['account.tax.retention.table'].search([
                ('city_id', '=', record.city_id.id)
            ], limit=1)
            if ica_setting and ica_setting.ica_tax_id:
                hierarchy = self.env['account.tax.hierarchy'].search([
                    ('parent_tax_id', '=', ica_setting.ica_tax_id.id)
                ], limit=1)
                if hierarchy:
                    tax_total_income = record._get_line_value('tax_charge_total_income')
                    amount_total = abs(tax_total_income * (hierarchy.amount / 100))
                    lines = record.line_ids.filtered(
                        lambda x: x.taxable_type == 'tax_advice_total_income')
                    for line in lines:
                        line.write({
                            'amount_move': abs(amount_total),
                            'amount_move_round': record._round_amount(abs(amount_total))
                        })

    def _compute_tax_charge_advice_total_income(self):
        for record in self:
            tax_total_income = record._get_line_value('tax_charge_total_income')
            tax_advice_total_income = record._get_line_value('tax_advice_total_income')
            amount_total = abs(tax_total_income + tax_advice_total_income)
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'tax_charge_advice_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_surcharge_total_income(self):
        for record in self:
            tax_total_income = record._get_line_value('tax_total_income')
            amount_total = abs(tax_total_income * (record.surcharge / 100))
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'surcharge_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_tax_surcharge_total_income(self):
        for record in self:
            tax_charge_advice_total_income = record._get_line_value('tax_charge_advice_total_income')
            surcharge_total_income = record._get_line_value('surcharge_total_income')
            amount_total = abs(tax_charge_advice_total_income + surcharge_total_income)
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'tax_surcharge_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_discount_total_income(self):
        for record in self:
            tax_charge_advice_total_income = record._get_line_value('tax_charge_advice_total_income')
            amount_total = abs(tax_charge_advice_total_income * (record.discount / 100))
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'discount_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })

    def _compute_net_tax_total_income(self):
        for record in self:
            tax_surcharge_total_income = record._get_line_value('tax_surcharge_total_income')
            discount_total_income = record._get_line_value('discount_total_income')
            amount_total = abs(tax_surcharge_total_income - discount_total_income)
            lines = record.line_ids.filtered(
                lambda x: x.taxable_type == 'net_tax_total_income')
            for line in lines:
                line.write({
                    'amount_move': amount_total,
                    'amount_move_round': record._round_amount(amount_total)
                })
