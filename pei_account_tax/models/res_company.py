from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_group_by_analytic = fields.Boolean(
        string='Agrupación por Cuentas Analíticas'
    )
    city_from_business = fields.Boolean(
        string='Ciudad del Negocio Seleccionado'
    )