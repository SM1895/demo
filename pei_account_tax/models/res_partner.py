from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ciiu_value_ids = fields.Many2many(
        comodel_name='ciiu.value',
        string='Códigos CIIU'
    )
    main_ciuu_id = fields.Many2one(
        comodel_name='ciiu.value',
        string='Actividad principal',
        domain="[('id', 'in', ciiu_value_ids)]"
    )

    @api.constrains('ciiu_value_ids')
    def _check_ciiu_value_ids(self):
        for record in self:
            if len(record.ciiu_value_ids) > 5:
                raise ValidationError(
                    'No es permitido tener más de 5 códigos CIIU añadidos.')
