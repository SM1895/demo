from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountExogenusFormat1001(models.TransientModel):
    _inherit = 'account.exogenus.print.reports'

    def _validate_lesser_amount(self, amount):
        amount = 0 if not amount else amount
        if float(amount) < self.exogenus_format_id.lesser_amount:
            return True
        return False

    def _validate_data_report_line(self, data_report_line):
        lesser_amount = False
        for data in data_report_line:
            if (data[1] == 'calculated' and data[2]
                    and self._validate_lesser_amount(data[0])):
                lesser_amount = True
        if lesser_amount:
            return [], data_report_line
        return data_report_line, []

    def _process_group_by_concept(self, data_group_concepts):
        data_order_by_concept = {}
        for data_line in data_group_concepts:
            data_concept = {}
            for line in data_line:
                if line[3] == '0':
                    if not data_order_by_concept.get(line[0], False):
                        data_order_by_concept[line[0]] = {
                            line[3]: line[0]}
                        data_concept = data_order_by_concept[line[0]]
                    else:
                        data_concept = data_order_by_concept[line[0]]
                else:
                    if line[1] == 'calculated':
                        if data_concept.get(line[3], False):
                            amount = (
                                float(line[0])
                                if line[0] != '' else 0)
                            data_concept[line[3]] = (
                                float(data_concept[line[3]])+amount)
                        else:
                            amount = (float(line[0])
                                      if line[0] != '' else 0)
                            data_concept[line[3]] = amount
                    else:
                        data_concept[line[3]] = line[0]
        return data_order_by_concept

    def _process_group_by_lesser_amount(self, data_group_lesser_amount):
        data_group_by_lesser_amount = {}
        for data_line in data_group_lesser_amount:
            for line in data_line:
                # data_group_by_lesser_amount[line[3]] = line[0]
                if line[1] == 'calculated':
                    if data_group_by_lesser_amount.get(line[3], False):
                        amount = (
                            float(line[0])
                            if line[0] != '' else 0)
                        data_group_by_lesser_amount[line[3]] = (
                            float(data_group_by_lesser_amount[line[3]])+amount)
                    else:
                        amount = (float(line[0])
                                  if line[0] != '' else 0)
                        data_group_by_lesser_amount[line[3]] = amount
                else:
                    data_group_by_lesser_amount[line[3]] = line[0]
                    # data_group_by_lesser_amount[line[3]] = line[0]
        return data_group_by_lesser_amount

    def _group_by_data_file(self, data_group_info):
        if self.exogenus_format_id.has_concepts:
            return self._process_group_by_concept(data_group_info)
        return self._process_group_by_lesser_amount(data_group_info)

    def _get_partner_less_amount(self):
        query = self._query_partner_information()
        query += "  WHERE rp.vat = '222222222'"
        self.env.cr.execute(query)
        info_report = self.env.cr.dictfetchall()
        return info_report

    def _get_data_column(self, columns_format, key, item,
                         partner_lesses_amount):
        value_item = None
        for column in columns_format:
            if column.sequence == int(key):
                item = ''
                value_item = column.account_format_column_id.execute_code(
                    partner_lesses_amount, self)
                break
        return value_item, item

    def _get_data_lesser_amount(self, data_order_by_concept):
        columns_format = self.env[
            'account.exogenus.formats.columns.sequence'].search(
                [('exogenus_format_id', '=', self.exogenus_format_id.id),
                 ('account_format_column_id.type_column', '=', 'data')])
        array_lesser_amount_group = []
        partner_lesses_amount = self._get_partner_less_amount()[0]
        print("_get_data_lesser_amount",data_order_by_concept)
        if (self.exogenus_format_id.has_smaller_amount
                and not self.exogenus_format_id.has_concepts):
            raise ValidationError("Se esta construyendo la logica")
        else:
            for values in data_order_by_concept.values():
                lesser_amount_line = []
                for key, item in values.items():
                    if self.exogenus_format_id.has_concepts and key == '0':
                        partner_lesses_amount['exogenus_concept_id'] = item
                    value_field, item = self._get_data_column(
                        columns_format, key, item, partner_lesses_amount)
                    if value_field is None:
                        lesser_amount_line.append(item)
                    else:
                        lesser_amount_line.append(value_field)
                array_lesser_amount_group.append(lesser_amount_line)
        return array_lesser_amount_group

    # Metodo para procesos valores que no estan dentro de la cuantia
    # menor
    def _process_data_without_lesser_amount(self, data_report_final):
        data_report_without_lesser = []
        for data in data_report_final:
            line_report_without_lesser = []
            for line in data:
                line_report_without_lesser.append(line[0])
            data_report_without_lesser.append(line_report_without_lesser)
        return data_report_without_lesser

    def _get_data_result_report(self):
        data_report = self.concept_and_smaller_amount()
        order_sequence = (
            self.exogenus_format_id.exogenus_formats_columns_ids.
            sorted(lambda r: r.sequence)
        )
        columns = []
        data_column = []
        for column_title in order_sequence:
            columns.append(column_title.account_format_column_id.name)
        data_report_final = []
        data_report_final_with_lesser = []
        for line in data_report:
            data_report_line = []
            data_with_lesser = []
            count = 0
            for data_field in order_sequence:
                if ((not self.exogenus_format_id.has_smaller_amount
                        and not self.exogenus_format_id.has_concepts) or
                    (not self.exogenus_format_id.has_smaller_amount
                        and self.exogenus_format_id.has_concepts)):
                    data_report_line.append(
                        data_field.account_format_column_id.execute_code(
                            line, self))
                else:
                    data_report_line.append(
                        (data_field.account_format_column_id.execute_code(
                            line, self),
                         data_field.account_format_column_id.type_column,
                         data_field.account_format_column_id.minior_amount,
                         '{}'.format(count)))
                count += 1
            if ((not self.exogenus_format_id.has_smaller_amount
                    and not self.exogenus_format_id.has_concepts) or
                (not self.exogenus_format_id.has_smaller_amount
                 and self.exogenus_format_id.has_concepts)):
                data_report_final.append(data_report_line)
            else:
                data_report_line, data_with_lesser = (
                    self._validate_data_report_line(
                        data_report_line))
                if data_report_line and not data_with_lesser:
                    data_report_final.append(data_report_line)
                elif not data_report_line and data_with_lesser:
                    data_report_final_with_lesser.append(
                        data_with_lesser)
        if (self.exogenus_format_id.has_smaller_amount
                and self.exogenus_format_id.has_concepts):
            data_order_by_concept = self._group_by_data_file(
                data_report_final_with_lesser)
            array_lesser_amount_group = self._get_data_lesser_amount(
                data_order_by_concept)
            data_report_final_print = self._process_data_without_lesser_amount(
                data_report_final)
            data_report_print = array_lesser_amount_group+data_report_final_print
            return data_report_print, columns
        if (self.exogenus_format_id.has_smaller_amount
                and not self.exogenus_format_id.has_concepts):
            data_order_by_concept = self._group_by_data_file(
                data_report_final_with_lesser)
            array_lesser_amount_group = self._get_data_lesser_amount(
                data_order_by_concept)
        return data_report_final, columns
