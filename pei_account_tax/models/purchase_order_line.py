from odoo import models, api, fields


class PurchaseOrderLine(models.Model): 
    _inherit = 'purchase.order.line'

    aiu_amount = fields.Float(
        string='AIU',
        compute='_compute_aiu_amount',
        store=True
    )

    @api.depends('order_id.tax_totals',
                 'order_id.aiu_line_ids',
                 'order_id.aiu',
                 'order_id.aiu_line_ids.amount')
    def _compute_aiu_amount(self):
        for record in self:
            record.aiu_amount = 0
            if record.order_id.aiu == 'yes':
                amount_base = 0
                total_aiu = record.order_id.amount_total_aiu
                subtotal = record.price_subtotal
                if record.order_id.tax_totals:
                    amount_base = record.order_id.tax_totals.get('amount_untaxed', 0)
                if subtotal and amount_base and total_aiu:
                    base_percentage = (subtotal / amount_base) * 100
                    record.aiu_amount = total_aiu * (base_percentage / 100)

    def _convert_to_tax_base_line_dict(self):
        if self.order_id.aiu_line_ids and self.order_id.aiu == 'yes':
            return self.env['account.tax']._convert_to_tax_base_line_dict(
                self,
                partner=self.order_id.partner_id,
                currency=self.order_id.currency_id,
                product=self.product_id,
                taxes=self.taxes_id,
                price_unit=self.price_unit,
                quantity=self.product_qty,
                price_subtotal=self.price_subtotal,
            )
        return super()._convert_to_tax_base_line_dict()
