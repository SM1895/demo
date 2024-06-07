from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_group_by_analytic = fields.Boolean(
        string='Agrupación por Cuentas Analíticas',
        readonly=False,
        related='company_id.account_group_by_analytic'
    )
    city_from_business = fields.Boolean(
        string='Ciudad del Negocio Seleccionado',
        readonly=False,
        related='company_id.city_from_business'
    )
