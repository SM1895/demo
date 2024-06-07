from odoo import api, fields, models

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def map_tax(self, taxes):
        result = super().map_tax(taxes)
        children = self.env["account.tax.hierarchy"].search([("child_tax_id", "in", result.ids), ("method", "=", "reteiva")])
        result |= children.parent_tax_id
        return result