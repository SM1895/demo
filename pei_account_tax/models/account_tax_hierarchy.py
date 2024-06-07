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

    def _compute_ica(self, line, taxes):
        ica_parent_taxes = self.search([("method", "=", "ica")])
        ica_children = ica_parent_taxes.filtered(lambda h: h.child_tax_id.id in taxes.ids)
        for t in ica_children:
            if line.partner_id.city_id != t.city_id or not((line.partner_id.main_ciuu_id) & t.ciiu_ids):
                taxes = (taxes - t.child_tax_id) | t.parent_tax_id
        ica_taxes = taxes.filtered(lambda t: t in ica_parent_taxes.parent_tax_id)
        taxes_correspondance = self.env['account.tax']
        for tax in ica_taxes:
            tax_correspondance_main = self.search([
                ("parent_tax_id", "=", tax.id),
                ("city_id", "=", line.partner_id.city_id.id),
            ]).filtered(lambda t: line.partner_id.main_ciuu_id & t.ciiu_ids).child_tax_id
            if tax_correspondance_main:
                taxes_correspondance |= tax_correspondance_main
            else:
                tax_correspondance_other = self.search([
                    ("parent_tax_id", "=", tax.id),
                    ("city_id", "=", line.partner_id.city_id.id),
                ]).filtered(lambda t: line.partner_id.other_ciiu_id & t.ciiu_ids).child_tax_id
                taxes_correspondance |= tax_correspondance_other
        if not taxes_correspondance:
            return taxes
        # return ica_taxes, taxes_correspondance
        return (taxes - ica_taxes) | taxes_correspondance

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
