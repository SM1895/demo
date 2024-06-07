# -*- coding: utf-8 -*-
from odoo import models, fields, SUPERUSER_ID

class l10nCoAddress(models.Model):
    _name = "l10n_co.address"
    _description = "Nomenclatura direcciones"
    _rec_name = "abbreviation"
    _order = "position"

    name = fields.Char('Nombre', required=True)
    abbreviation = fields.Char('Abreviación', required=True)
    type_id = fields.Many2one(
        comodel_name='l10n_co.address.type', string='Tipo', 
        group_expand='_group_expand_type_id', required=True)
    position = fields.Selection(related="type_id.position", store=True)

    def _group_expand_type_id(self, types, domain, order):
        type_ids = types._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return types.browse(type_ids)

class l10nCoAddressType(models.Model):
    _name = "l10n_co.address.type"
    _description = "Tipos nomenclatura direcciones"
    _order = "position"

    name = fields.Char('Nombre', required=True)
    position = fields.Selection([("1","1"), ("2","2"), ("3","3"), ("4","4")], string="Posición")