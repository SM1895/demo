from odoo.tools.misc import xlsxwriter


class GenerateXLSX():
    def __init__(self, output, data_report, format_name, data_columns):
        self.output = output
        self.data_report = data_report
        self.format_name = format_name
        self.data_columns = data_columns

    def generate_report_xlsx(self):
        workbook = xlsxwriter.Workbook(self.output, {
            'in_memory': True,
            'strings_to_formulas': False})
        sheet = workbook.add_worksheet('{}'.format(self.format_name))
        row = 0
        col = 0
        for column in self.data_columns:
            sheet.write(row, col, column)
            col += 1
        row = 1
        for data_result in self.data_report:
            col = 0
            for data in data_result:
                sheet.write(row, col, data)
                col+=1
            row += 1
        workbook.close()
        return self.output
