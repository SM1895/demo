# -*- coding: utf-8 -*-

from odoo import models, fields

class l10nLatamIdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    doc_type_code = fields.Char('Código')
    dv_required = fields.Boolean('DV Requerido')