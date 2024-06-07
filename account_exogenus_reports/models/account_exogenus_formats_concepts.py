# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class AccountExogenusFormatsConcepts(models.Model):
    _name = 'account.exogenus.formats.concepts'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    exogenus_format_id = fields.Many2one(
        'account.exogenus.formats', string="Format Exogenus", required=True)
    concept_exogenus_account_ids = fields.One2many(
        'account.exogenus.formats.concepts.account', 'exogenus_concept_id',
        string="Concept Account")

    def action_select_account(self):
        return {
            'name': _('select account'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.concept.account.wizard',
            'target': 'new',
            'context': {'default_account_exogenus_format_concept_id': self.id}
        }
