import logging
from odoo import fields, models, _
from io import BytesIO
import base64
from ..models.account_exogenus_formats_generate_xlsx import GenerateXLSX


class AccountExogenusPrintXls(models.TransientModel):
    _name = 'account.exogenus.print.reports'

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    exogenus_format_id = fields.Many2one(
        'account.exogenus.formats', string="Format Exogenus", required=True)
    format_type = fields.Selection(
        related="exogenus_format_id.format_type",
        string="Format type")
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    file_filename = fields.Char(string='File Name')
    file_binary = fields.Binary(string='File')

    def generate_xlsx(self, output):
        data_report, data_columns = self._get_data_result_report()
        generate_xlsx = GenerateXLSX(
            output, data_report, self.exogenus_format_id.name, data_columns)
        return generate_xlsx.generate_report_xlsx()

    def print_document_xlsx(self):
        output = BytesIO()
        output = self.generate_xlsx(output)
        output.seek(0)
        return base64.b64encode(output.getvalue())

    def action_generate_report(self):
        get_data = self.print_document_xlsx()
        self.write({
            'file_filename': self.exogenus_format_id.name+'.xlsx',
            'file_binary': get_data
        })
        return {
            'context': self.env.context,
            'name': _("Print Report Account Exogenus"),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.exogenus.print.reports',
            'res_id': self.id,
            'view_id': self.env.ref('account_exogenus_reports.'
                                    'account_exogenus_print_reports').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def concept_and_smaller_amount(self):
        data = []
        if (self.exogenus_format_id.has_concepts):
            data = self.excute_concept_and_smaller_amount()
        else:
            data = self.excute_without_concept()
        return data if len(data) else []
