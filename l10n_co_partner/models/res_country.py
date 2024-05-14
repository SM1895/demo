# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCountry(models.Model):
    _inherit = "res.country"

    dian_code = fields.Char('Código')
    co_address = fields.Boolean('Estructura dirección CO')
