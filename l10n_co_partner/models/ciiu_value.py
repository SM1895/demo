# -*- coding: utf-8 -*-

from odoo import models, fields

class CiiuValue(models.Model):
    _name = "ciiu.value"
    _description = "Códigos CIIU"
    _rec_name = "code"

    industry = fields.Char('División')
    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True)
