from ast import Invert
from odoo import api, models, fields
from odoo.exceptions import UserError
import logging


class AccountTaxAIUConcepts(models.Model):
    _name = 'account.tax.aiu.concepts'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string='Concepto AIU',
        required=True
    )
    type = fields.Selection(
        string='Tipo de AIU',
        selection=[
            ("temp_services", "Servicios Temporales de Aseo y Vigilancia"),
            ("civil_contract", "Contratos de Obra Civil")
        ],
        required=True
    )
    aiu_type_concepts_ids = fields.One2many(
        comodel_name='account.tax.aiu.type.concepts',
        inverse_name='aiu_concepts_id',
        string='Conceptos',
        required=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for record in vals_list:
            company_id = self.env.company.id
            type = record.get("type", False)
            old_tax = self.env['account.tax.aiu.concepts'].search([
                "&",
                ('company_id', '=', company_id),
                ('type', '=', type),
            ]).ids
            if len(old_tax) > 0:
                raise UserError(f"Ya hay un Concepto creado con el tipo \"{str(type)}\" para esta compañía. No se permite continuar.")

        res = super().create(vals_list)
        return res

    def write(self, vals):
        if "company_id" in vals or "type" in vals:
            company_id = vals.get("company_id", {}).get("id", False) if vals.get("company_id", False) else self.company_id.id
            type = vals.get("type", False) if vals.get("type", False) else self.type
            old_tax = self.env['account.tax.aiu.concepts'].search([
                "&",
                ('company_id', '=', company_id),
                ('type', '=', type),
            ]).ids
            if len(old_tax) > 0:
                raise UserError("Ya hay un Concepto creado con el tipo " + type + " para esta compañía, no se permite continuar.")
        res = super().write(vals)
        return res
    
class AccountTaxAIUTypeConcepts(models.Model):
    _name = 'account.tax.aiu.type.concepts'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.aiu_concepts_id.company_id
    )
    name = fields.Char(
        string='Concepto',
        required=True
    )
    tax_to_apply = fields.Many2many(
        comodel_name='account.tax',
        string='Impuestos a Aplicar'
    )
    aiu_concepts_id = fields.Many2one(
        comodel_name='account.tax.aiu.concepts',
        string='Conceptos'
    )

    @api.onchange('tax_to_apply')
    def _onchange_tax_to_apply(self):
        selected_tax = self.aiu_concepts_id.aiu_type_concepts_ids.filtered(lambda x: x.tax_to_apply)
        selected_tax = selected_tax.mapped('tax_to_apply')
        return {
            'domain': {
                'tax_to_apply': [('id', 'not in', selected_tax.ids)]
            }
        }
