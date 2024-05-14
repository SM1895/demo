from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        document_base = sum(self.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')).mapped('price_subtotal'))
        if document_base:
            self.env.context = dict(self.env.context)
            self.env.context.update({'document_base': document_base})
        res = super()._compute_tax_totals()
        return res

    def write(self, values):
        super().write(values)
        document_base = sum(self.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')).mapped('price_subtotal'))
        if document_base:
            self.env.context = dict(self.env.context)
            self.env.context.update({'document_base': document_base})

    @api.onchange('partner_id')
    def _onchange_partner_tax_id(self):
        self.invoice_line_ids._onchange_tax_ids()
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id', 'move_id.partner_id', 'price_unit')
    def _compute_all_tax(self):
        res = super(AccountMoveLine, self)._compute_all_tax()
        for line in self:
            document_base = sum(line.move_id.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')).mapped('price_subtotal'))
            if not document_base:
                document_base = line.price_subtotal
            self.env.context = dict(self.env.context)
            self.env.context.update({'document_base': document_base})
        return res

    def _get_computed_taxes(self):
        self.ensure_one()
        tax_ids = super()._get_computed_taxes()
        if tax_ids:
            taxes = self.env["account.tax.hierarchy"]._compute_ica(self, tax_ids)
            taxes = self.env["account.tax.hierarchy"]._compute_reteiva(taxes, self.product_id)
            return taxes
        return tax_ids
    
    @api.onchange('tax_ids', 'partner_id')
    def _onchange_tax_ids(self):
        for line in self:
            taxes = self.env["account.tax.hierarchy"]._compute_ica(line, line.tax_ids._origin)
            taxes = self.env["account.tax.hierarchy"]._compute_reteiva(taxes, line.product_id)
            line.tax_ids = taxes

