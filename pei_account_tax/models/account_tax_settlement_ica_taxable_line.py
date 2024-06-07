from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountTaxSettlementIcaTaxableLine(models.Model):
    _name = 'account.tax.settlement.ica.taxable.line'
    _description = 'Detalle Liquidación ICA'

    settlement_id = fields.Many2one(
        comodel_name='account.tax.settlement.ica.taxable',
        string='Detalle de Liquidación'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id'
    )
    amount_move = fields.Monetary(
        string='Movimiento',
        currency_field='company_currency_id'
    )
    amount_move_round = fields.Float(
        string='Redondeo',
    )
    taxable_type = fields.Selection(
        selection=[
            ('total_income', 'Ingreso Total'),
            ('out_total_income', 'Ingresos Fuera del Municipio'),
            ('total_income_city', 'Total Ingresos en Este Municipio'),
            ('return_total_income', 'Ingresos por Devoluciones, Rebajas y Descuentos'),
            ('export_total_income', 'Ingresos por Exportaciones'),
            ('sale_total_income', 'Ingresos por Ventas de Activos Fijos'),
            ('exclude_total_income', 'Ingresos no Sujetos y/o Excluidos'),
            ('exempt_total_income', 'Ingresos Exentos en este Municipio'),
            ('taxable_total_income', 'Total Ingresos Gravables'),
            ('tax_total_income', 'Impuesto de Industria y Comercio Bruto'),
            ('retention_total_income', 'Autorretenciones'),
            ('total_positive_balance', 'Total Saldo a Favor'),
            ('tax_charge_total_income', 'Total Impuesto Industria y Comercio a Cargo'),
            ('tax_advice_total_income', 'Impuesto de Avisos y Tableros'),
            ('tax_charge_advice_total_income', 'Total Impuesto de Industria y Comercio + Avisos y Tableros'),
            ('surcharge_total_income', 'Sobretasa Bomberil'),
            ('tax_surcharge_total_income', 'Total Impuesto a Cargo'),
            ('discount_total_income', 'Descuento por Pronto Pago'),
            ('net_tax_total_income', 'Impuesto Neto a Pagar por el Año Gravable')
        ],
        string='Detalle de Ingresos'
    )
    is_bold = fields.Boolean(
        string='Negrilla',
        compute='_compute_is_bold',
        store=True
    )

    @api.depends('taxable_type')
    def _compute_is_bold(self):
        for record in self:
            record.is_bold = False
            if record.taxable_type in self._get_bold_details():
                record.is_bold = True

    def _get_bold_details(self):
        return [
            'total_income',
            'total_income_city',
            'taxable_total_income',
            'retention_total_income',
            'tax_charge_total_income',
            'tax_charge_advice_total_income',
            'tax_surcharge_total_income',
            'net_tax_total_income'
        ]
