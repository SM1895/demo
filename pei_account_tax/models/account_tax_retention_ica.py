# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountTaxRetentionIca(models.Model):
    _name = "account.tax.retention.ica"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proceso Retención de ICA'

    name = fields.Char(
        string='Nombre',
        racking=True
    )
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Ciudad',
        racking=True
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Asiento Contable'
    )
    income_line_ids = fields.One2many(
        comodel_name='account.tax.retention.income',
        inverse_name='retention_id',
        string='Líneas de Ingreso',
    )
    audit_line_ids = fields.One2many(
        comodel_name='account.tax.retention.partner',
        inverse_name='retention_id',
        string='Líneas de Auditoria',
    )
    date_from = fields.Date(
        string='Fecha Inicial',
        tracking=True
    )
    date_to = fields.Date(
        string='Fecha Final',
        tracking=True
    )
    account_setting_id = fields.Many2one(
        comodel_name='account.tax.retention.ica.account',
        string='Configuración Contable',
        tracking=True
    )
    min_base_retention = fields.Monetary(
        string='Base mínima Retención Calculada',
        currency_field='company_currency_id',
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
    account_group_by_analytic = fields.Boolean(
        string="Agrupacion",
        related='company_id.account_group_by_analytic'
    )
    city_from_business = fields.Boolean(
        string="Agrupacion por ciudad",
        related='company_id.city_from_business'
    )
    domain_cities_ids = fields.Many2many(
        comodel_name='res.city',
        relation='tax_retention_city_rel',
        column1='retention_id',
        column2='city_id',
        string='Dominio Ciudades'
    )
    is_main_company = fields.Boolean(
        string='Es PEI'
    )
    readonly_city = fields.Boolean(
        string='Ciudad Lectura',
        compute='compute_readonly_city',
        store=True
    )

    @api.depends('is_main_company', 'city_from_business', 'account_group_by_analytic')
    def compute_readonly_city(self):
        for record in self:
            if record.is_main_company and self.env.company.account_group_by_analytic:
                record.readonly_city = False
            else:
                record.readonly_city = True

    def compute_income_values(self):
        for record in self:
            if record.min_base_retention <= 0:
                raise ValidationError(
                    'El valor de la base minima para la retención debe ser superior a cero.')
            record.income_line_ids._create_detail_lines()

    def compute_partner_values(self):
        for record in self:
            record.audit_line_ids.unlink()
            fideicomiso = self.env['res.fideicomiso'].search([
                ('vat', '=', self.env.company.company_registry)
            ], limit=1)
            if fideicomiso:
                record._create_audit_lines(fideicomiso)
    
    def _get_goups_ciiu(self):
        dict_groups = {}
        for line in self.income_line_ids:
            if line.ciiu_id.id not in dict_groups.keys():
                dict_groups[line.ciiu_id.id] = {
                    'amount_retention': line.amount_retention,
                    'ciiu_id': line.ciiu_id
                }
            else:
                dict_groups[line.ciiu_id.id]['amount_retention'] += line.amount_retention
        return dict_groups

    def _create_audit_lines(self, fideicomiso):
        dict_groups = self._get_goups_ciiu()
        for beneficiary in fideicomiso.beneficiary_ids.filtered(
                lambda x: x.partner_id and x.participation_percentage):
            if beneficiary.partner_id.property_account_position_id.is_retention:
                factor = 1
            else:
                factor = 0
            for ciuu, vals in dict_groups.items():
                self.env['account.tax.retention.partner'].create({
                    'partner_id': beneficiary.partner_id.id,
                    'participation_percentage': beneficiary.participation_percentage,
                    'fiscal_position_id': beneficiary.partner_id.property_account_position_id.id,
                    'ciiu_id': ciuu,
                    'amount_retention': vals.get('amount_retention') * beneficiary.participation_percentage * factor,
                    'retention_id': self.id
                })

    def create_account_move(self):
        for record in self:
            if record.move_id:
                raise ValidationError('Este registro tiene un asiento contable creado y asociado.')
            if not record.audit_line_ids:
                raise ValidationError('No hay lineas de terceros y auditoria.')
            if sum(x.amount_retention for x in record.audit_line_ids) == 0:
                raise ValidationError(
                    'No se puede generar un asiento con el total de retención en cero.')
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': record.account_setting_id.journal_id.id,
                'line_ids': record._get_move_lines()
            }
            move = self.env['account.move'].create(move_vals)
            record.sudo().move_id = move

    def _get_move_lines(self):
        line_ids = []
        dict_partners = {}
        total_amount = 0
        for line in self.audit_line_ids.filtered(lambda x: x.amount_retention != 0):
            if line.partner_id.id not in dict_partners:
                dict_partners[line.partner_id.id] = {
                    'amount': line.amount_retention
                }
            else:
                dict_partners[line.partner_id.id]['amount'] += line.amount_retention
        for partner, vals in dict_partners.items():
            total_amount += abs(vals.get('amount'))
            line_ids.append((0, 0, {
                'partner_id': partner,
                'debit': abs(vals.get('amount')),
                'account_id': self.account_setting_id.partner_account_id.id
            }))
        line_ids.append((0, 0, {
            'credit': total_amount,
            'account_id': self.account_setting_id.payable_account_id.id
        }))
        return line_ids
    
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'account.tax.retention.ica' or self._name == 'account.tax.retention.ica':
            cities = [
                x.city_id.id for x in self.env['account.tax.retention.ica.group'].search([])]
            defaults['domain_cities_ids'] = [(6, 0, cities)]
            if self.env.company.name == 'Patrimonio Autónomo Estrategias Inmobiliarias PEI':
                defaults.update(
                    is_main_company=True
                )
            else:
                if self.env.company.city_from_business:
                    fideicomiso = self.env['res.fideicomiso'].search([
                        ('vat', '=', self.env.company.company_registry)
                    ], limit=1)
                    if fideicomiso:
                        defaults.update(
                            city_id=fideicomiso.city_of_execution_id.id,
                        )
                    else:
                        if self.env.company.city_id:
                            defaults.update(
                                city_id=self.env.company.city_id.id,
                            )
        return defaults

    def add_massive_accounts(self):
        self.ensure_one()
        wizard = self.env['account.tax.income.massive.wizard'].create({
            'retention_id': self.id
        })
        for line in self.income_line_ids.filtered(lambda x: x.account_id):
            wizard.domain_account_ids += line.account_id
        return {
            'name': 'Agregar Cuentas',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.tax.income.massive.wizard',
            'target': 'new',
            'res_id': wizard.id
        }

    def unlink(self):
        for record in self:
            if record.move_id:
                raise ValidationError(
                    'Este registro no puede ser eliminado, debido a que se ha realizado un movimiento contable.')
            record.income_line_ids.unlink()
            record.audit_line_ids.unlink()
        return super().unlink()
