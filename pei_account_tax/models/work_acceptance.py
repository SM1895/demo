from odoo import models, api, fields


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    def create_invoice(self):
        res = super().create_invoice()
        if self.invoice_id and self.purchase_id.aiu == 'yes':
            self.invoice_id.aiu = self.purchase_id.aiu
            self.invoice_id.aiu_type = self.purchase_id.aiu_type
            if self.invoice_id.is_main_company:
                self.invoice_id.from_oc_pei = True
            for line in self.purchase_id.aiu_line_ids:
                line.invoice_percentage = line.percentage
                self.invoice_id.aiu_line_ids += line
        return res
