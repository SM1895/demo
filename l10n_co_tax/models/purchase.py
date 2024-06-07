from odoo import api, fields, models
from odoo.exceptions import ValidationError



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    @api.onchange('partner_id')
    def _onchange_partner_tax_id(self):
        self.order_line._onchange_taxes_id()

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()
        for order in self:
            self.env.context = dict(self.env.context)
            self.env.context.update({'document_base': order.amount_untaxed})
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
        return res
    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_tax_id(self):
        super()._compute_tax_id()
        TaxHierarchy = self.env["account.tax.hierarchy"]
        for line in self:
            taxes = TaxHierarchy._compute_ica(line, line.taxes_id)
            taxes = TaxHierarchy._compute_reteiva(taxes)
            line.taxes_id = taxes

    @api.onchange('taxes_id', 'partner_id')
    def _onchange_taxes_id(self):
        TaxHierarchy = self.env["account.tax.hierarchy"]
        for line in self:
            taxes = TaxHierarchy._compute_ica(line, line.taxes_id._origin)
            taxes = TaxHierarchy._compute_reteiva(taxes)
            line.taxes_id = taxes
