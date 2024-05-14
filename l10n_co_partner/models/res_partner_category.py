# -*- coding: utf-8 -*-
# Copyright 2024 Alejandro Olano ( Sysman SAS), jaramirez@sysman.com.co

from odoo import models, api
from odoo.exceptions import ValidationError


class ResPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    @api.model
    def create(self, values):
        res = super().create(values)
        if values.get("name") == "partner_categ":
            return res
        else:
            for r in res:
                if r.name == values.get("name"):
                    raise ValidationError(
                        "Ya Existe la Etiqueta %s en la Base de Datos" % (r.name)
                    )
        return res
