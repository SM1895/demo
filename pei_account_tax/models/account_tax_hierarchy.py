# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountTaxHierarchy(models.Model):
    _inherit = "account.tax.hierarchy"

    method = fields.Selection(
        selection_add=[("sobreica", "Sobretasa ICA")],
        ondelete={'sobreica': 'cascade'}
    )
    ica_child_tax_id = fields.Many2one(
        "account.tax",string="Sobretasa ICA")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    @api.onchange('ica_child_tax_id')
    def _onchange_ica_child_tax_id(self):
        for record in self:
            if record.ica_child_tax_id:
                record.child_tax_id = record.ica_child_tax_id
            else:
                record.child_tax_id = False
    
    @api.onchange('method')
    def _onchange_method(self):
        for record in self:
            if record.method != 'sobreica':
                record.ica_child_tax_id = False

    def _compute_sobreica(self, taxes, product_id=False, partner_id=False):
        orphan = taxes & self.search([("method", "=", "sobreica")]).filtered(lambda h: h.parent_tax_id.id not in taxes.ids).child_tax_id
        excule_tax_ids = []
        if partner_id and partner_id.property_account_position_id:
            excule_tax_ids = [
                x.tax_src_id.id for x in partner_id.property_account_position_id.tax_ids.filtered(
                    lambda x: not x.tax_dest_id)]
        if orphan:
            taxes = taxes - orphan
        domain = [("method", "=", "sobreica")]
        if product_id:
            domain.append('|'),
            domain.append((("detailed_type"), "=", False)),
            domain.append((("detailed_type"), "=", product_id.detailed_type))
        orphan = self.search(domain).filtered(
            lambda h: h.parent_tax_id.id in taxes.ids and h.child_tax_id.id not in excule_tax_ids).child_tax_id
        if orphan:  
            taxes += orphan
        return taxes

    def unlink(self):
        for record in self:
            tax_ids = self.env['account.tax'].search([
                '|',
                '|',
                ('hierarchy1_id', '=', record.id),
                ('hierarchy2_id', '=', record.id),
                ('hierarchy3_id', '=', record.id),
            ])
            if tax_ids:
                raise ValidationError(
                    'No se puede eliminar una jerarquía '
                    'creada a partir de una sobretasa ica.')
        super().unlink()
