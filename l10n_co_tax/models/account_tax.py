# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountTax(models.Model):
    _inherit = "account.tax"

    ##### BASE GRAVABLE FIELDS
    tax_apply_base = fields.Boolean('Tax apply base?')
    tax_apply_base_condition = fields.Selection([
        ('greater', '>'),
        ('greater or equal', '>='),
        ('smaller', '<'),
        ('less or equal', '<='),
        ('equal', '='),
    ], default="greater")
    tax_apply_base_value = fields.Float('Base Value')

    ##### TAX HIERARCHY FIELDS (ICA AND RETEIVA)
    tax_hierarchy = fields.Boolean("Jerarquía Impuestos", related="l10n_co_edi_type.tax_hierarchy", store=True)
    parent_tax_count = fields.Integer("Parent Tax Count")
    children_tax_count = fields.Integer("Children Tax Count")

    def _compute_tax_count(self, r=0):
        for rec in self:
            TaxHierarchy = rec.env["account.tax.hierarchy"]
            parent_tax_count = len(TaxHierarchy.search([("child_tax_id", "=", rec.id)]))
            children_tax_count = len(TaxHierarchy.search([("parent_tax_id", "=", rec.id)]))

            rec.parent_tax_count = 0 if parent_tax_count < 0 else parent_tax_count
            rec.children_tax_count = 0 if children_tax_count < 0 else children_tax_count
    
    def _update_tax_counts(self):
        for rec in self:
            rec.parent_tax_id._compute_tax_count()
            rec.child_tax_id._compute_tax_count()


    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
        self.ensure_one()

        amount_untaxed_base = self.env.context.get('document_base') if 'document_base' in self.env.context else False
        if self.tax_apply_base and amount_untaxed_base:
            if self.tax_apply_base_condition == 'greater' and amount_untaxed_base <= self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'greater or equal' and amount_untaxed_base < self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'smaller' and amount_untaxed_base >= self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'less or equal' and amount_untaxed_base > self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'equal' and self.tax_apply_base_value != amount_untaxed_base:
                return 0.0
        
        taxc = self.env["account.tax.hierarchy"].search([("child_tax_id", "=", self.id), ("method", "=", "reteiva")])
        if taxc:
            parent = taxc.parent_tax_id.with_context(parent_tax=taxc.parent_tax_id.id)._compute_amount(base_amount, price_unit, quantity, product, partner, fixed_multiplicator)
            return parent * self.amount/100

        return super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner, fixed_multiplicator)
    
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):
        if product and product._name == 'product.template':
            product = product.product_variant_id
        Hierarchy = self.env["account.tax.hierarchy"]
        orphan = self & Hierarchy.search([("method", "=", "reteiva")]).filtered(lambda h: h.parent_tax_id.id not in self.ids).child_tax_id
        if orphan and not self.env.context.get('ignore_hierarchy_reteiva'):
            self = self - orphan
        return super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund=is_refund, handle_price_include=handle_price_include, include_caba_tags=include_caba_tags, fixed_multiplicator=fixed_multiplicator)

class L10nCoEdiTaxType(models.Model):
    _inherit = "l10n_co_edi.tax.type"

    tax_hierarchy = fields.Boolean("Jerarquía Impuestos")