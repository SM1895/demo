# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class AccountExogenusFormats(models.Model):
    _name = 'account.exogenus.formats'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    format_type = fields.Selection(selection=[
        ('dian', 'DIAN'), ('district', 'District')], string="Type",
        required=True)
    exogenus_formats_concept_ids = fields.One2many(
        'account.exogenus.formats.concepts',
        'exogenus_format_id',
        string="Format Concepts")
    exogenus_formats_columns_ids = fields.One2many(
        'account.exogenus.formats.columns.sequence',
        'exogenus_format_id',
        string="Format Columns")
    has_smaller_amount = fields.Boolean(string='Has Smaller Amount')
    lesser_amount = fields.Float(string='Lesser Amount')
    has_concepts = fields.Boolean(string='Has Concepts')

