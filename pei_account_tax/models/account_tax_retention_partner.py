# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountTaxRetentionPartner(models.Model):
    _name = 'account.tax.retention.partner'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Beneficiario',
        tracking=True
    )
    participation_percentage = fields.Float(
        string='% De Participación',
        tracking=True
    )
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string='Posición Fiscal',
        tracking=True
    )
    ciiu_id = fields.Many2one(
        comodel_name='ciiu.value',
        string='Código CIIU',
        tracking=True
    )
    amount_retention = fields.Monetary(
        string='Retención Calculada',
        currency_field='company_currency_id',
        tracking=True
    )
    retention_id = fields.Many2one(
        comodel_name='account.tax.retention.ica',
        string='Retención',
    ) 
    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True
    )
