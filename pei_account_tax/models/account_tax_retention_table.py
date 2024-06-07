from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountTaxRetentionTable(models.Model):
    _name = 'account.tax.retention.table'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tabla de Retencion de ICA y RET ICA'

    name = fields.Char(
        string='Nombre',
        tracking=True
    )
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Departamento',
        tracking=True
    )
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Ciudad',
        tracking=True
    )
    ciiu_activity_id = fields.Many2one(
        string='Actividad Económica CIIU',
        comodel_name='ciiu.value',
        tracking=True
    )
    fee_ica = fields.Float(
        string='Tarifa ICA',
        compute='_compute_tax_settings',
        store=True,
        tracking=True
    )
    fee_retention = fields.Float(
        string='Tarifa de Retención',
        compute='_compute_tax_settings',
        store=True,
        tracking=True
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta Contable ICA',
        compute='_compute_tax_settings',
        store=True,
        tracking=True
    )
    rte_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta Contable Retención',
        compute='_compute_tax_settings',
        store=True,
        tracking=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        tracking=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    ica_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Impuesto ICA',
        tracking=True
    )
    rteica_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Impuesto RETE ICA',
        tracking=True
    )
    ica_type = fields.Selection(
        selection=[
            ('rete_ica', 'Retención de ICA'),
            ('ica', 'ICA')
        ],
        string='Tipo'
    )

    def _update_name(self):
        self.name = self.ciiu_activity_id.name

    @api.onchange('active')
    def _onchange_active(self):
        for record in self:
            if record.ica_tax_id:
                record.ica_tax_id.active = record.active
            if record.rteica_tax_id:
                record.rteica_tax_id.active = record.active

    @api.onchange('ciiu_activity_id',
                  'ica_type')
    def _onchange_ciiu_activity_id(self):
        for record in self:
            if record.ica_type == 'rete_ica':
                record._update_name()

    @api.depends('ica_tax_id', 'rteica_tax_id')
    def _compute_tax_settings(self):
        for record in self:
            record.account_id = False
            record.rte_account_id = False
            record.fee_retention = record.rteica_tax_id.amount
            record.fee_ica = record.ica_tax_id.amount
            line = record.ica_tax_id.invoice_repartition_line_ids.filtered(
                lambda x: x.account_id)
            if line:
                record.account_id = line[0].account_id
            
            line_rte = record.rteica_tax_id.invoice_repartition_line_ids.filtered(
                lambda x: x.account_id)
            if line_rte:
                record.rte_account_id = line_rte[0].account_id

    def create_table_tax(self, vals):
        for record in self:
            ica_vals = {
                'name': vals['name'] + ' ICA ' + str(vals['fee_ica']) + '%',
                'amount_type': 'percent',
                'amount': vals['fee_ica'],
                'type_tax_use': 'purchase',
            }
            ica_tax = self.env['account.tax'].create(ica_vals)
            for line in ica_tax.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax'):
                line.account_id = vals['account_id']
            for line in ica_tax.refund_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax'):
                line.account_id = vals['account_id']
            rte_vals = {
                'name': vals['name'] + ' RTE ICA ' + str(vals['fee_retention']) + '%',
                'amount_type': 'percent',
                'amount': vals['fee_retention'],
                'type_tax_use': 'purchase',
            }
            ret_tax = self.env['account.tax'].create(rte_vals)
            for line in ret_tax.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax'):
                line.account_id = vals['rte_account_id']
            for line in ret_tax.refund_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax'):
                line.account_id = vals['rte_account_id']
            record.ica_tax_id = ica_tax
            record.rteica_tax_id = ret_tax

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            domain = [
                ('name', '=', record.name),
                ('id', '!=', record.id)]
            if self.env['account.tax.retention.table'].search(domain):
                raise ValidationError(
                    'Ya existe un registro con el mismo nombre.')

    @api.constrains('city_id', 'ciiu_activity_id')
    def _check_unique_ciiu(self):
        for record in self:
            records = self.search([
                ('city_id', '=', record.city_id.id),
                ('ciiu_activity_id', '=', record.ciiu_activity_id.id),
                ('active', '=', True),
                ('id', '!=', record.id)
            ])
            if records:
                raise ValidationError(
                    'Ya existe una configuración activa para la ciudad y actividad CIIU.')
    
    def _check_fee(self):
        for record in self:
            if record.fee_ica <= 0 or record.fee_ica > 100:
                raise ValidationError(
                    'El valor de la Tarifa ICA debe ser mayor a 0 e inferior a 100.')
            if record.fee_retention == 0:
                raise ValidationError(
                    'El valor de Tarifa de Retención no puede ser igual a 0.')
            if record.fee_retention < -100 or record.fee_retention > 100:
                raise ValidationError(
                    'El valor de Tarifa de Retención debe ser mayor a -100 e inferior a 100.')

    def _compute_reteica(self, taxes, partner_id=False):
        orphan = taxes & self.search([]).filtered(lambda h: h.ica_tax_id.id not in taxes.ids).rteica_tax_id
        if orphan:
            taxes = taxes - orphan[0]
        excule_tax_ids = []
        if partner_id and partner_id.property_account_position_id:
            excule_tax_ids = [
                x.tax_src_id.id for x in partner_id.property_account_position_id.tax_ids.filtered(
                    lambda x: not x.tax_dest_id)]
        orphan = self.search([]).filtered(
            lambda h: h.ica_tax_id.id in taxes.ids and h.rteica_tax_id.id not in excule_tax_ids).rteica_tax_id
        if orphan:
            taxes += orphan[0]
        return taxes
