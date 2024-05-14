from odoo import models, api, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
        inverse_name='purchase_id',
    )
    amount_total_aiu = fields.Float(
        string='Valor Total AIU',
        compute='_compute_amount_total_aiu',
        store=True
    )

    @api.depends('aiu_line_ids',
                 'aiu_line_ids.amount')
    def _compute_amount_total_aiu(self):
        for record in self:
            record.amount_total_aiu = sum(
                [x.amount for x in record.aiu_line_ids])

    def compute_aiu_amount(self):
        self.order_line._compute_aiu_amount()

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

    def excute_compute(self):
        for record in self:
            record.aiu_line_ids._compute_base_amount()

    @api.depends_context('lang')
    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self.filtered(lambda x: x.aiu == 'yes' and x.aiu_line_ids):
            context = self.env.context.copy()
            tax_with_other_base = order._get_dict_tax_other_base()
            if tax_with_other_base:
                context.update({
                    'other_base_tax': tax_with_other_base
                })
            order_lines = order.with_context(context).order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            self -= order
        return super()._compute_tax_totals()

    def _get_dict_tax_other_base(self):
        dict_vals = {}
        if self.aiu == 'yes' and self.aiu_type == 'temp_services' and self.aiu_line_ids:
            base = sum([x.price_subtotal for x in self.order_line])
            for line in self.aiu_line_ids.filtered(
                    lambda x: x.setting_id.tax_to_apply):
                for tax_apply in line.setting_id.tax_to_apply:
                    dict_vals[tax_apply.id] = {
                        'base': base * line.percentage,
                        'remaining': base * line.percentage,
                        'base_other_tax': base * line.percentage
                    }
        elif self.aiu == 'yes' and self.aiu_type == 'civil_contract' and self.aiu_line_ids:
            base = sum([x.price_subtotal for x in self.order_line])
            base_extra = (sum([x.percentage * base for x in self.aiu_line_ids])) + base
            for line in self.aiu_line_ids.filtered(
                    lambda x: x.setting_id.tax_to_apply):
                for tax_apply in line.setting_id.tax_to_apply:
                    if tax_apply.utility_base:
                        dict_vals[tax_apply.id] = {
                            'base': base * line.percentage,
                            'remaining': base * line.percentage,
                            'base_other_tax': base * line.percentage
                        }
                    else:
                        dict_vals[tax_apply.id] = {
                            'base': base_extra,
                            'remaining': base_extra,
                            'base_other_tax': 0
                        }
        return dict_vals
