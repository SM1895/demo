# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountTaxHierarchy(models.Model):
    _name = "account.tax.hierarchy"
    _description = "Tax Hierarchy"
    _rec_name = "parent_tax_id"
    # check_company=True

    parent_tax_id = fields.Many2one("account.tax",string="Impuesto Padre", required=True)
    child_tax_id = fields.Many2one("account.tax",string="Impuesto Hijo", required=True)
    amount = fields.Float("Importe", related="child_tax_id.amount")
    ciiu_ids = fields.Many2many("ciiu.value", string="CIIU Values")
    city_id = fields.Many2one("res.city",string="Ciudad")
    method = fields.Selection([("ica", "Avisos y Tableros"), ("reteiva", "ReteIVA")], string="Método", required=True)
    detailed_type = fields.Selection([
        ('consu', 'Consumible'),
        ('service', 'Servicio')], string='Tipo de Producto', default='all')

    @api.constrains('ciiu_ids','city_id', 'method', 'parent_tax_id')
    def _check_identification(self):    
        for rec in self.filtered(lambda s: s.method == "ica"):
            tax = self.search([("parent_tax_id", "=", rec.parent_tax_id.id), ("city_id", "=", rec.city_id.id)]) - self
            if tax.filtered(lambda t: t.ciiu_ids & rec.ciiu_ids):
                raise ValidationError("Condiciones encontradas en otro impuesto")

    @api.onchange("parent_tax_id", "child_tax_id")
    def _onchange_tax_counts(self):
        for rec in self:
            rec.parent_tax_id._origin._compute_tax_count()
            rec.child_tax_id._origin._compute_tax_count()
            rec.parent_tax_id._compute_tax_count()
            rec.child_tax_id._compute_tax_count()
            
    @api.model_create_multi
    def create(self, vals):
        res = super(AccountTaxHierarchy, self).create(vals)
        res.parent_tax_id._compute_tax_count()
        res.child_tax_id._compute_tax_count()
        return res

    def unlink(self):
        for rec in self:
            parent_tax_id = rec.parent_tax_id
            child_tax_id = rec.child_tax_id
            res = super(AccountTaxHierarchy, self).unlink()
            parent_tax_id._compute_tax_count()
            child_tax_id._compute_tax_count()
        return res

    def _compute_ica(self, line, taxes):
        ica_parent_taxes = self.search([("method", "=", "ica")])
        ica_children = ica_parent_taxes.filtered(lambda h: h.child_tax_id.id in taxes.ids)
        for t in ica_children:
            if line.partner_id.city_id != t.city_id or not((line.partner_id.main_ciiu_id | line.partner_id.other_ciiu_id) & t.ciiu_ids):
                taxes = (taxes - t.child_tax_id) | t.parent_tax_id
        ica_taxes = taxes.filtered(lambda t: t in ica_parent_taxes.parent_tax_id)
        taxes_correspondance = self.env['account.tax']
        for tax in ica_taxes:
            tax_correspondance_main = self.search([
                ("parent_tax_id", "=", tax.id),
                ("city_id", "=", line.partner_id.city_id.id),
            ]).filtered(lambda t: line.partner_id.main_ciiu_id & t.ciiu_ids).child_tax_id
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

    def _compute_reteiva(self, taxes, product_id=False):
        orphan = taxes & self.search([("method", "=", "reteiva")]).filtered(lambda h: h.parent_tax_id.id not in taxes.ids).child_tax_id
        if orphan:
            taxes = taxes - orphan
        domain = [("method", "=", "reteiva")]
        if product_id:
            domain.append((("detailed_type"), "=", product_id.detailed_type))
        orphan = self.search(domain).filtered(
            lambda h: h.parent_tax_id.id in taxes.ids).child_tax_id
        if orphan:
            taxes += orphan
        return taxes
