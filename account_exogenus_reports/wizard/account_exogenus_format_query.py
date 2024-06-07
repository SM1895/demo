from odoo import fields, models, _


class AccountExogenusFormat1001(models.TransientModel):
    _inherit = 'account.exogenus.print.reports'

    def _drop_temporary_table(self):
        self.env.cr.execute("DROP TABLE temp_account_exogenus_report")

    def _get_temporary_table(self):
        query = "SELECT * FROM temp_account_exogenus_report"
        return query

    def _get_process_aml_dict(self, aml_dict):
        amls_ids = []
        if len(aml_dict) > 0:
            for aml in aml_dict:
                amls_ids.append(aml.get('id'))
        return amls_ids

    def _get_values_move_by_dates(self):
        query = ("SELECT aml.id FROM account_move_line aml "
                 "WHERE aml.date >= %(date_from)s AND aml.date <= %(date_to)s "
                 "AND aml.parent_state = 'posted' "
                 "AND aml.company_id = %(company_id)s "
                 )
        params = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
        }
        if self.exogenus_format_id.has_concepts:
            concepts = self.env[
                'account.exogenus.formats.concepts'].search(
                    [('exogenus_format_id', '=', self.exogenus_format_id.id)])
            account_concepts = concepts.mapped(
                'concept_exogenus_account_ids.account_id')
            params['account_ids'] = (
                tuple(account_concepts.ids) if account_concepts else ())
            query += (
                "AND aml.account_id in %(account_ids)s "
                if account_concepts else "")
        self.env.cr.execute(query, params)
        aml_dict = self.env.cr.dictfetchall()
        amls_ids = self._get_process_aml_dict(aml_dict)
        return amls_ids

    def _query_partner_information(self):
        query = ("SELECT  rp.id, llaid.l10n_co_document_code,rp.vat,rp.name,"
                 "rp.street,rcity.zipcode,rc.code AS country_code,"
                 "rcs.code as state_code "
                 "FROM res_partner rp "
                 "INNER JOIN l10n_latam_identification_type llaid "
                 "ON (rp.l10n_latam_identification_type_id = llaid.id) "
                 "LEFT JOIN res_country_state rcs ON (rp.state_id = rcs.id) "
                 "LEFT JOIN res_country rc ON (rp.country_id = rc.id) "
                 "LEFT JOIN res_city rcity ON (rp.city_id = rcity.id) "
                 )
        return query

    def _query_with_concept_and_smaller_amount(self):
        query = (
            "with rp AS ({}), "
            "csa AS "
            "(SELECT aefca.exogenus_concept_id, rp.l10n_co_document_code,"
            "rp.vat,rp.name,rp.street,rp.zipcode,rp.country_code,"
            "aml.partner_id,rp.state_code"
            " FROM rp "
            " LEFT JOIN account_move_line aml ON (aml.partner_id = rp.id)"
            " LEFT JOIN account_exogenus_formats_concepts_account aefca"
            " ON (aefca.account_id = aml.account_id)"
            " LEFT JOIN account_exogenus_formats_concepts aefc ON"
            " (aefca.exogenus_concept_id = aefc.id)"
            " WHERE aml.partner_id is not null"
            " AND aefc.exogenus_format_id = %(exogenus_format_id)s"
            " AND aml.company_id = %(company_id)s "
            " AND aml.partner_id = rp.id"
            " AND aml.id in %(amls_ids)s"
            " GROUP BY aefca.exogenus_concept_id, rp.l10n_co_document_code,"
            " rp.vat,rp.name,rp.street,rp.zipcode,rp.country_code,"
            " aml.partner_id,rp.state_code)"
            " SELECT  * INTO TEMPORARY temp_account_exogenus_report from csa;"
        ).format(self._query_partner_information())
        return query

    def excute_concept_and_smaller_amount(self):
        amls_ids = self._get_values_move_by_dates()
        params = {
            'exogenus_format_id': self.exogenus_format_id.id,
            'company_id': self.company_id.id,
            'amls_ids': tuple(amls_ids)
        }
        query_tbl_temp = self._get_temporary_table()
        data_query = self._query_with_concept_and_smaller_amount()
        self.env.cr.execute(data_query+query_tbl_temp, params)
        info_report = self.env.cr.dictfetchall()
        self._drop_temporary_table()
        return info_report

    def _query_without_concept(self):
        query = (
            "with rp AS ({}), "
            "csa AS "
            "(SELECT rp.l10n_co_document_code,"
            "rp.vat,rp.name,rp.street,rp.zipcode,rp.country_code,"
            "aml.partner_id,rp.state_code"
            " FROM rp "
            " LEFT JOIN account_move_line aml ON (aml.partner_id = rp.id)"
            " WHERE aml.partner_id is not null"
            " AND aml.company_id = %(company_id)s "
            " AND aml.partner_id = rp.id"
            " AND aml.id in %(amls_ids)s"
            " GROUP BY rp.l10n_co_document_code,"
            " rp.vat,rp.name,rp.street,rp.zipcode,rp.country_code,"
            " aml.partner_id,rp.state_code)"
            " SELECT  * INTO TEMPORARY temp_account_exogenus_report from csa;"
        ).format(self._query_partner_information())
        return query

    def excute_without_concept(self):
        amls_ids = self._get_values_move_by_dates()
        params = {
            'company_id': self.company_id.id,
            'amls_ids': tuple(amls_ids)
        }
        query_tbl_temp = self._get_temporary_table()
        data_query = self._query_without_concept()
        self.env.cr.execute(data_query+query_tbl_temp, params)
        info_report = self.env.cr.dictfetchall()
        self._drop_temporary_table()
        return info_report
