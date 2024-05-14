from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountTaxApportionmentLine(models.Model):
    _name = 'account.tax.apportionment.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Prorrateo de IVA Linea'

    company_id = fields.Many2one(
        string='Compañía',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    apportionment_id = fields.Many2one(
        comodel_name='account.tax.apportionment',
        string='Prorrateo IVA',
    )
    apportionment_type = fields.Selection(
        selection=[
            ('iva', 'IVA'),
            ('income', 'Ingreso'),
        ],
        string='Tipo de Linea'
    )
    amount_moves = fields.Float(
        string='Movimiento Contable',
    )
    amount_reject_iva = fields.Float(
        string='IVA Rechazado',
    )
    percentage = fields.Float(
        string='Proporción de la Categoría de Ingreso / Total de movimiento',
    )
    apportionment_group_id = fields.Many2one(
        comodel_name='account.tax.apportionment.group',
        string='Categorización de Ingreso'
    )
    apportionment_iva_id = fields.Many2one(
        comodel_name='account.tax.apportionment.iva',
        string='Categorización de IVA'
    )
    exclued_moves_ids = fields.Many2many(
        comodel_name='account.move.line',
        string='Movimientos Exlcuidos',
    )
    detail_ids = fields.One2many(
        comodel_name='account.tax.apportionment.detail',
        inverse_name='line_id',
        string='Detalles'
    )

    def action_view_audit(self):
        self.ensure_one()
        view_id = self.env.ref(
            'pei_account_tax.account_tax_apportionment_group_line_view_form').id
        if self.apportionment_type == 'income':
            name = self.apportionment_group_id.name
        else:
            name = self.apportionment_iva_id.name
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'account.tax.apportionment.line',
            'res_id': self.id,
        }

    def action_view_moves(self):
        return {
            'name': 'Movimientos',
            'type': 'ir.actions.act_window',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'domain': [('id', 'in', self.exclued_moves_ids.ids)],
        }

    def unlink(self):
        for record in self:
            record.detail_ids.unlink()
        return super().unlink()
