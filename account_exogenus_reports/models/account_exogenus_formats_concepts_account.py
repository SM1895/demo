# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class AccountExogenusFormatsConceptsAccount(models.Model):
    _name = 'account.exogenus.formats.concepts.account'

    name = fields.Char(string='Name', required=True,
                       related="exogenus_concept_id.code")
    exogenus_concept_id = fields.Many2one(
        'account.exogenus.formats.concepts',
        string="Format Exogenus", required=True)

    account_id = fields.Many2one(
        'account.account',
        string="Account", required=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
