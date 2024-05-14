# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountTaxRetentionIcaGroup(models.Model):
    _name = "account.tax.retention.ica.group"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Configuración Mapeo Ciudad y Analítico'

    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Ciudad',
    )
    account_analytics_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        relation='retention_ica_account_rel',
        column1='retention_id',
        column2='account_id',
        string='Analítico'
    )
    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    city_from_business = fields.Boolean(
        string='Agrupacion por ciudad',
        related='company_id.city_from_business',
        compute='_compute_city_from_business',
        store=True
    )

    @api.depends('company_id.city_from_business')
    def _compute_city_from_business(self):
        for record in self:
            record.city_from_business = record.company_id.city_from_business

    @api.model_create_multi
    def create(self, vals_list):
        self._check_city_from_business()
        return super().create(vals_list)

    def write(self, vals):
        self._check_city_from_business()
        return super().write(vals)    

    @api.constrains('account_analytics_ids')
    def _check_accounts(self):
        for record in self:
            record._check_city_from_business()
            if record.account_analytics_ids.ids:
                account_ids = record.account_analytics_ids.ids 
                account_ids.append(0)
                self._cr.execute(
                    'SELECT count(*) FROM retention_ica_account_rel WHERE account_id IN %s AND retention_id <> %s' % (
                        tuple(account_ids), record.id))
                result = self._cr.fetchone()
                if result[0] != 0:
                    raise ValidationError(
                        'Una de las cuentas analíticas seleccionadas ya ha sido configurada para otra ciudad.')

    def _check_city_from_business(self):
        if self.env.company.city_from_business:
            raise ValidationError('No se pueden realizar configuraciones '
                                  'ya que el negocio esta marcado como con ciudad de ejecución.')

    def action_read_group(self):
        self.ensure_one()
        return {
            'name': self.city_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.tax.retention.ica.group',
            'res_id': self.id,
        }
