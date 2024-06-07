# -*- coding: utf-8 -*-
# Copyright 2023 Jonathan Medina <Github@jmedis4>

import re
import logging

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    category_id = fields.Many2many(comodel_name="res.partner.category", required=True)

    dv = fields.Char("DV", compute="_compute_dv", default=False, readonly=False)
    dv_required = fields.Boolean(
        "Usar DV", related="l10n_latam_identification_type_id.dv_required"
    )
    co_address = fields.Boolean(related="country_id.co_address")
    co_street_1 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_2 = fields.Char()
    co_street_3 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_4 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_5 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_6 = fields.Char()
    co_street_7 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_8 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_9 = fields.Char()
    co_street_10 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_11 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_12 = fields.Char()
    co_street_13 = fields.Many2one(comodel_name="l10n_co.address")
    co_street_14 = fields.Char()
    co_street_15 = fields.Many2one(comodel_name="l10n_co.address")
    # co_street_15 = fields.Many2one(comodel_name="l10n_co.address", domain=[('type_id.position', '=', 4)])
    co_street_16 = fields.Char()
    checked = fields.Boolean()

    main_ciiu_id = fields.Many2one(comodel_name="ciiu.value", string="CIIU Primario")
    other_ciiu_id = fields.Many2one(comodel_name="ciiu.value", string="CIIU Secundario")

    @api.constrains("l10n_latam_identification_type_id", "vat")
    def _check_identification(self):
        context = self.env.context or {}
        if not context.get("from_api_rest_update"):
            for rec in self:
                if rec.vat:
                    query = """
                        select id
                        from res_partner 
                        where vat='%s' 
                        and l10n_latam_identification_type_id='%s' 
                        and parent_id IS NULL
                    """ % (
                        rec.vat,
                        rec.l10n_latam_identification_type_id.id,
                    )
                    self.env.cr.execute(query)
                    line_ids = list(line[0] for line in self.env.cr.fetchall())
                    if not rec.parent_id and rec.id in line_ids:
                        line_ids.remove(rec.id)
                    if line_ids and not rec.parent_id:
                        raise ValidationError(
                            "El Número de identificación %s ya existe con este tipo de identificación asociado a este contacto %s"
                            % (
                                rec.vat,
                                self.env["res.partner"].browse(line_ids[0]).name,
                            )
                        )
        if context.get("from_api_rest"):
            for rec in self:
                if rec.parent_id:
                    partner = self.env["res.partner"].search(
                        [("id", "=", rec.parent_id.id)]
                    )
                    if (
                        partner.vat != rec.vat
                        and rec.l10n_latam_identification_type_id.id == 4
                    ):
                        raise ValidationError(
                            "El Número de identificación %s es diferente al de la Compañia Padre %s"
                            % (rec.vat, partner.name)
                        )

    @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    def check_vat(self):
        # return super(ResPartner, self).check_vat()
        # check_vat is implemented by base_vat which this localization
        # doesn't directly depend on. It is however automatically
        # installed for Colombia.
        if any(partner.dv_required for partner in self):
            return True
        else:
            return super(ResPartner, self).check_vat()

    @api.depends("vat", "l10n_latam_identification_type_id")
    def _compute_dv(self):
        for rec in self:
            if rec.vat and rec.l10n_latam_identification_type_id.dv_required:
                factors = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
                vat = re.sub(r"[^0-9]", "", rec.vat)
                fit_vat = vat.rjust(15, "0")
                res = sum(int(fit_vat[14 - i]) * factors[i] for i in range(14)) % 11
                result = 11 - res if res > 1 else res
                rec.dv = str(result)
            else:
                rec.dv = False
            # return str(result)

    @api.model
    def _concat_args(self, *argv):
        args = tuple(filter(lambda x: x, argv))
        return " ".join(args)
        # return " ".join(map(str.upper, args))

    # concatenación Dirección tipo DIAN
    @api.onchange(
        "country_id",
        "co_street_1",
        "co_street_2",
        "co_street_3",
        "co_street_4",
        "co_street_5",
        "co_street_6",
        "co_street_7",
        "co_street_8",
        "co_street_9",
        "co_street_10",
        "co_street_11",
        "co_street_12",
        "co_street_13",
        "co_street_14",
        "co_street_15",
        "co_street_16",
    )
    def _onchange_street_fields(self):
        self.street = self._concat_args(
            self.co_street_1.name,
            self.co_street_2,
            self.co_street_3.name,
            self.co_street_4.name,
            self.co_street_5.name,
            (
                "No."
                if self.co_street_1.name and self.co_street_2 and self.co_street_6
                else False
            ),
            self.co_street_6,
            self.co_street_7.name,
            self.co_street_8.name,
            "-" if self.co_street_6 and self.co_street_9 else False,
            self.co_street_9,
            self.co_street_10.name,
            self.co_street_11.name,
            self.co_street_12,
            self.co_street_13.name,
            self.co_street_14,
            self.co_street_15.name,
            self.co_street_16,
        )

    @api.model
    def create(self, values):
        context = self.env.context or {}
        if not self.env.su:
            if (
                (
                    context.get("from_api_rest")
                    and not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_api"
                    )
                )
                or (
                    context.get("_import_current_module")
                    and not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_import_csv"
                    )
                )
                or (
                    not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_form"
                    )
                )
            ):
                raise ValidationError(
                    _("No tiene permisos suficientes para realizar esta acción.")
                )
        res = super().create(values)
        if not res.name:
            raise ValidationError(_("El Campo Nombre es Obligatorio"))
        identification_type = self.env["l10n_latam.identification.type"].search(
            [("id", "=", res.l10n_latam_identification_type_id.id)]
        )
        if not identification_type:
            raise ValidationError(_("El Campo Tipo de Identificacion no es Valido"))

        return res

    def write(self, values):
        context = self.env.context or {}
        if not self.env.su:
            if (
                (
                    context.get("from_api_rest")
                    and not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_api"
                    )
                )
                or (
                    context.get("_import_current_module")
                    and not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_import_csv"
                    )
                )
                or (
                    not self.env.user.has_group(
                        "l10n_co_partner.group_res_partner_edit_form"
                    )
                )
            ):
                raise ValidationError(
                    _("No tiene permisos suficientes para realizar esta acción.")
                )

        return super().write(values)

    @api.model
    def cron_validate_bondholders_fork(self):
        partner_category_id = []
        category_id = []
        category_id_obj = (
            self.env["res.partner.category"]
            .search([("name", "=", "Tenedor")], limit=1)
            .id
        )
        partner_obj = self.env["res.partner"].search(
            [("category_id", "=", category_id_obj)]
        )
        if partner_obj:
            category_id.append(category_id_obj)
            for record in partner_obj:
                for r in record.category_id:
                    partner_category_id.append(r.id)
                obligations_parther = self.env["financial.holder.obligations"].search(
                    [("identification_number", "=", record.vat)]
                )
                if not obligations_parther:
                    for i in partner_category_id:
                        if i == category_id[0]:
                            partner_category_id.remove(i)
                    partner = self.env["res.partner"].search([("id", "=", record.id)])
                    partner.write({"category_id": partner_category_id})
                partner_category_id.clear()

    @api.model
    def cron_validate_bondholders_investor(self):
        partner_category_id = []
        category_id = []
        category_id_obj = (
            self.env["res.partner.category"]
            .search([("name", "=", "Inversionistas")], limit=1)
            .id
        )
        partner_obj = self.env["res.partner"].search(
            [("category_id", "=", category_id_obj)]
        )
        if partner_obj:
            category_id.append(category_id_obj)
            for record in partner_obj:
                for r in record.category_id:
                    partner_category_id.append(r.id)
                obligations_parther = self.env["financial.holder.obligations"].search(
                    [("identification_number", "=", record.vat)]
                )
                if not obligations_parther:
                    for i in partner_category_id:
                        if i == category_id[0]:
                            partner_category_id.remove(i)
                    partner = self.env["res.partner"].search([("id", "=", record.id)])
                    partner.write({"category_id": partner_category_id})
                partner_category_id.clear()

    @api.model
    def cron_contract_administration_tenants(self):
        partner_category_id = []
        category_id = []
        category_id_obj = (
            self.env["res.partner.category"]
            .search([("name", "=", "Arrendatario")], limit=1)
            .id
        )
        partner_obj = self.env["res.partner"].search(
            [("category_id", "=", category_id_obj)]
        )
        if partner_obj:
            category_id.append(category_id_obj)
            for record in partner_obj:
                for r in record.category_id:
                    partner_category_id.append(r.id)
                contract_parther = self.env["contract.administration"].search(
                    [("vat", "=", record.vat)]
                )
                if not contract_parther:
                    for i in partner_category_id:
                        if i == category_id[0]:
                            partner_category_id.remove(i)
                    partner = self.env["res.partner"].search([("id", "=", record.id)])
                    partner.write({"category_id": partner_category_id})
                partner_category_id.clear()
