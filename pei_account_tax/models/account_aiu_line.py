from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountAiuLine(models.Model):
    _name = 'account.aiu.line'

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Orden de Compra'
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura'
    )
    name = fields.Char(
        string='Concepto',
        compute='_compute_name',
        store=True
    )
    percentage = fields.Float(
        string='Porcentaje',
    )
    invoice_percentage = fields.Float(
        string='Porcentaje Factura',
    )
    setting_id = fields.Many2one(
        comodel_name='account.tax.aiu.type.concepts',
        string='Configuración'
    )
    amount = fields.Float(
        string='Valor',
        compute='_compute_amount',
        store=True
    )
    amount_invoice = fields.Float(
        string='Valor Factura',
        compute='_compute_amount_invoice',
        store=True
    )
    base_amount = fields.Float(
        string='Monto Base',
        compute='_compute_base_amount',
        store=True
    )
    base_amount_invoice = fields.Float(
        string='Monto Base Factura',
        compute='_compute_base_amount_invoice',
        store=True
    )

    @api.depends('purchase_id.tax_totals')
    def _compute_base_amount(self):
        for record in self:
            record.base_amount = 0
            if record.purchase_id.tax_totals:
                record.base_amount = record.purchase_id.tax_totals.get('amount_untaxed', 0)

    @api.depends('move_id.tax_totals')
    def _compute_base_amount_invoice(self):
        for record in self:
            record.base_amount_invoice = 0
            subtotal = 0
            for line in record.move_id.invoice_line_ids:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                subtotal += line.quantity * line_discount_price_unit
            if record.move_id.tax_totals:
                record.base_amount_invoice = subtotal

    @api.depends('base_amount', 'percentage')
    def _compute_amount(self):
        for record in self:
            record.amount = record.base_amount * record.percentage

    @api.depends('base_amount_invoice', 'invoice_percentage')
    def _compute_amount_invoice(self):
        for record in self:
            record.amount_invoice = record.base_amount_invoice * record.invoice_percentage

    @api.depends('setting_id')
    def _compute_name(self):
        for record in self:
            record.name = False
            if record.setting_id:
                record.name = record.setting_id.name

    @api.constrains('percentage')
    def _check_percentage(self):
        for record in self:
            if record.percentage < 0 or record.percentage > 100:
                raise ValidationError(
                    'El porcentage debe ser mayor a 0 e inferior a 100')

    @api.constrains('invoice_percentage')
    def _check_invoice_percentage(self):
        for record in self:
            if record.invoice_percentage < 0 or record.invoice_percentage > 100:
                raise ValidationError(
                    'El porcentage debe ser mayor a 0 e inferior a 100')
