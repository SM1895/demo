from odoo import models, api, fields
from odoo.tools import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    aiu = fields.Selection(
        selection=[
            ('yes', 'Si'),
            ('no', 'No')
        ],
        string='AIU',
        default='no'
    )
    aiu_type = fields.Selection(
        selection=[
            ('temp_services', 'Servicios Temporales de Aseo y Vigilancia'),
            ('civil_contract', 'Contratos de Obra Civil')
        ],
        string='Tipo AIU'
    )
    aiu_line_ids = fields.One2many(
        comodel_name='account.aiu.line',
        inverse_name='move_id',
    )
    from_oc_pei = fields.Boolean(
        string='Viene de Ordén de Compra PEI'
    )
    is_main_company = fields.Boolean(
        string='Es Pei',
        compute='_compute_is_main_company',
        store=True
    )
    amount_total_aiu = fields.Float(
        string='Valor Total AIU',
        compute='_compute_amount_total_aiu',
        store=True
    )

    @api.depends('aiu_line_ids',
                 'aiu_line_ids.amount_invoice')
    def _compute_amount_total_aiu(self):
        for record in self:
            record.amount_total_aiu = sum(
                [x.amount_invoice for x in record.aiu_line_ids])

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record._update_tax_analytic()
        return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            record._update_tax_analytic()
        return res

    def _update_tax_analytic(self):
        for record in self:
            for line in record.line_ids.filtered(
                    lambda x: x.tax_line_id and x.tax_line_id.inherit_analytic):
                record._get_json_analytic_tax(line)
            if record.line_ids.filtered(
                    lambda x: x.tax_line_id and x.tax_line_id.inherit_analytic):
                record.with_context(
                    add_analityc=True)._get_json_analytic()

    @api.onchange('aiu_type')
    def _onchange_aiu_type(self):
        for record in self:
            record.aiu_line_ids = False
            setting = self.env['account.tax.aiu.concepts'].search([
                ('type', '=', record.aiu_type),
                ('company_id', '=', record.company_id.id),
            ], limit=1)
            if setting:
                vals = record._create_vals_aiu(setting)
                if vals:
                    record.aiu_line_ids = vals

    def _create_vals_aiu(self, setting):
        vals = []
        for line in setting.aiu_type_concepts_ids:
            vals.append((0, 0, {
                'percentage': 0,
                'amount': 0,
                'setting_id': line.id
            }))
        return vals

    def _get_json_analytic_tax(self, line_to_write):
        new_json_analytic = {}
        tax_json_values = {}
        total_percentage = 0
        context = self.env.context.copy()
        context['ignore_hierarchy_reteiva'] = True
        if context.get('other_base_tax'):
            context.pop('other_base_tax')
        for line in self.line_ids.filtered(lambda x: x.account_id.account_type not in
                ('liability_payable', 'asset_receivable') and line_to_write.tax_line_id.id in x.tax_ids.ids
                and x.balance != 0):
            tax_dict = line_to_write.with_context(context).tax_line_id.compute_all(abs(line.balance))
            if tax_dict['taxes']:
                value = tax_dict['taxes'][0]['amount']
                if isinstance(line.analytic_distribution, dict):
                    for key, val in line.analytic_distribution.items():
                        tax_value_base = value * (val / 100)
                        if key not in tax_json_values.keys():
                            tax_json_values[key] = {
                                'value': tax_value_base
                            }
                        else:
                            tax_json_values[key]['value'] += tax_value_base
            total_percentage += 100
        for key, val in tax_json_values.items():
            if abs(line_to_write.balance) == 0:
                continue
            new_json_analytic[key] = (abs(val['value']) * 100) / abs(line_to_write.balance)
        line_to_write.analytic_distribution = new_json_analytic

    @api.depends('company_id')
    def _compute_is_main_company(self):
        for record in self:
            if record.company_id.name == 'Patrimonio Autónomo Estrategias Inmobiliarias PEI':
                record.is_main_company = True

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
        'aiu_line_ids.invoice_percentage',
        'aiu'
    )
    def _compute_tax_totals(self):
        for move in self:
            if move.is_invoice(include_receipts=True) and move.aiu == 'yes' and (move.aiu_line_ids or self.env.context.get('aiu_line_ids')):
                context = self.env.context.copy()
                tax_with_other_base = move._get_dict_tax_other_base()
                if tax_with_other_base:
                    context.update({
                        'other_base_tax': tax_with_other_base,
                    })
                base_lines = move.with_context(context).invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                sign = move.direction_sign
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    base_line_values_list += [
                        {
                            **line.with_context(context)._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.with_context(context).line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line.with_context(context)._convert_to_tax_line_dict()
                        for line in move.with_context(context).line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                            extra_context={'_extra_grouping_key_': 'epd'},
                        ))
                move.tax_totals = self.env['account.tax'].with_context(context)._prepare_tax_totals(**kwargs)
                if move.invoice_cash_rounding_id:
                    rounding_amount = move.invoice_cash_rounding_id.compute_difference(move.currency_id, move.tax_totals['amount_total'])
                    totals = move.tax_totals
                    totals['display_rounding'] = True
                    if rounding_amount:
                        if move.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                            totals['rounding_amount'] = rounding_amount
                            totals['formatted_rounding_amount'] = formatLang(self.env, totals['rounding_amount'], currency_obj=move.currency_id)
                            totals['amount_total_rounded'] = totals['amount_total'] + rounding_amount
                            totals['formatted_amount_total_rounded'] = formatLang(self.env, totals['amount_total_rounded'], currency_obj=move.currency_id)
                        elif move.invoice_cash_rounding_id.strategy == 'biggest_tax':
                            if totals['subtotals_order']:
                                max_tax_group = max((
                                    tax_group
                                    for tax_groups in totals['groups_by_subtotal'].values()
                                    for tax_group in tax_groups
                                ), key=lambda tax_group: tax_group['tax_group_amount'])
                                max_tax_group['tax_group_amount'] += rounding_amount
                                max_tax_group['formatted_tax_group_amount'] = formatLang(self.env, max_tax_group['tax_group_amount'], currency_obj=move.currency_id)
                                totals['amount_total'] += rounding_amount
                                totals['formatted_amount_total'] = formatLang(self.env, totals['amount_total'], currency_obj=move.currency_id)
                self -= move
        return super()._compute_tax_totals()

    def _get_dict_tax_other_base(self):
        dict_vals = {}
        if self.aiu == 'yes' and self.aiu_type == 'temp_services' and (self.aiu_line_ids or self.env.context.get('aiu_line_ids')):
            base = 0
            for line in self.invoice_line_ids:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                base += line.quantity * line_discount_price_unit
            if self.aiu_line_ids:
                aiu_line_ids = self.aiu_line_ids
            elif self.env.context.get('aiu_line_ids'):
                aiu_line_ids = self.env.context.get('aiu_line_ids')
            for line in aiu_line_ids.filtered(
                    lambda x: x.setting_id.tax_to_apply):
                for tax_apply in line.setting_id.tax_to_apply:
                    dict_vals[tax_apply.id] = {
                        'base': base * line.invoice_percentage,
                        'remaining': base * line.invoice_percentage,
                        'base_other_tax': base * line.invoice_percentage
                    }
        elif self.aiu == 'yes' and self.aiu_type == 'civil_contract' and (self.aiu_line_ids or self.env.context.get('aiu_line_ids')):
            base = 0
            for line in self.invoice_line_ids:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                base += line.quantity * line_discount_price_unit
            base_extra = (sum([x.invoice_percentage * base for x in self.aiu_line_ids])) + base
            if self.aiu_line_ids:
                aiu_line_ids = self.aiu_line_ids
            elif self.env.context.get('aiu_line_ids'):
                aiu_line_ids = self.env.context.get('aiu_line_ids')
            for line in aiu_line_ids.filtered(
                    lambda x: x.setting_id.tax_to_apply):
                for tax_apply in line.setting_id.tax_to_apply:
                    if tax_apply.utility_base:
                        dict_vals[tax_apply.id] = {
                            'base': base * line.invoice_percentage,
                            'remaining': base * line.invoice_percentage,
                            'base_other_tax': base * line.invoice_percentage
                        }
                    else:
                        dict_vals[tax_apply.id] = {
                            'base': base_extra,
                            'remaining': base_extra,
                            'base_other_tax': 0
                        }
        return dict_vals
