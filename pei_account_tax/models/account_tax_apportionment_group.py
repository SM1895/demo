from odoo import models, api, fields
from odoo.exceptions import ValidationError
import re


class AccountTaxApportionmentGroup(models.Model):
    _name = 'account.tax.apportionment.group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Configuración Prorrateo de IVA'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    name = fields.Char(
        string='Categorización de Ingresos',
        tracking=True
    )
    accounts_ids = fields.Many2many(
        string='Cuenta Contable',
        relation='apportionment_group_account_rel',
        column1='apportionment_id',
        column2='account_id',
        comodel_name='account.account',
        tracking=True
    )
    exclude_from_compute = fields.Boolean(
        string='Excluir del Calculo',
        tracking=True
    )

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if record.name:
                record._validate_name()
    
    @api.constrains('accounts_ids')
    def _check_accounts(self):
        for record in self:
            if record.accounts_ids:
                account_ids = record.accounts_ids.ids 
                account_ids.append(0)
                self._cr.execute(
                    'SELECT count(*) FROM apportionment_group_account_rel WHERE account_id IN %s AND apportionment_id <> %s' % (
                        tuple(account_ids), record.id))
                result = self._cr.fetchone()
                if result[0] != 0:
                    raise ValidationError(
                        'Una de las cuentas seleccionadas ya ha sido configurada en otro registro.')

    def write(self, vals):
        account_ids = self.accounts_ids.ids
        res = super().write(vals)
        new_account_ids = self.accounts_ids.ids
        if not self.env.user.has_group(
                'pei_account_tax.account_tax_apportionment_admin'):
            for account in account_ids:
                if account not in new_account_ids:
                    raise ValidationError(
                        'No se puede remover una cuenta contable previamente configurada.')
        if vals.get('accounts_ids'):
            self.tracking_account_ids(account_ids, new_account_ids)
        return res

    def _validate_name(self):
        pattern = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s]*$'
        if not re.match(pattern, self.name):
            raise ValidationError('El nombre del la configuración '
                                  'no puede contener carácteres especiales.')

    def action_read_group(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.tax.apportionment.group',
            'res_id': self.id,
        }

    def tracking_account_ids(self, old_accounts, new_account_ids):
        msg_pre = ''
        msg_new = ''
        pre_accounts = self.env['account.account'].search([
            ('id', 'in', old_accounts)
        ])
        post_accounts = self.env['account.account'].search([
            ('id', 'in', new_account_ids)
        ])
        if pre_accounts:
            msg_pre = ''
            for account in pre_accounts:
                msg_pre += ' * ' + account.name + '<br/>'
        msg = '<ul class="o_Message_trackingValues mb-0 ps-4">'
        for account in post_accounts:
            msg_new += ' * ' + account.name + '<br/>'
        msg += '<li>'
        msg += '<div class="o_TrackingValue d-flex align-items-center flex-wrap mb-1" role="group">'
        msg += '<span class="o_TrackingValue_oldValue me-1 px-1 text-muted fw-bold">'
        msg += msg_pre
        msg += '</span>'
        msg += '<i class="o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600" title="Cambiado" role="img" aria-label="Changed"></i>'
        msg += '<span class="o_TrackingValue_newValue me-1 fw-bold text-info">'
        msg += msg_new
        msg += '</span>'
        msg += '<span class="o_TrackingValue_fieldName ms-1 fst-italic text-muted">'
        msg += '(Cuenta Contable)'
        msg += '</span>'
        msg += '<div>'
        msg += '</li>'
        msg += '</ul>'
        self.message_post(body=msg)