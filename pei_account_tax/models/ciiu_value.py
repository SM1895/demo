from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CiiuValue(models.Model):
    _inherit = 'ciiu.value'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Tercero',
    )

    @api.onchange('code')
    def _onchange_code(self):
        for record in self:
            if record.code:
                record.name = record.code

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.partner_id:
                if self.search([
                        ('partner_id', '=', record.partner_id.id),
                        ('code', '=', record.code),
                        ('id', '!=', record.id)]):
                    raise ValidationError(
                        'No es permitido tener dos registros '
                        'con el mismo código para el mismo tercero')
