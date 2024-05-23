from odoo import api, fields, models, _
from odoo.tools import frozendict
from contextlib import contextmanager


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    retention_table_id = fields.Many2one(
        comodel_name='account.tax.retention.table',
        string='Tarifa'
    )
    aiu_amount = fields.Float(
        string='AIU',
        compute='_compute_aiu_amount',
        store=True
    )

    @api.depends('price_unit',
                 'move_id.aiu_line_ids',
                 'move_id.aiu')
    def _compute_aiu_amount(self):
        for record in self.filtered(
                lambda x: x.display_type == 'product'):
            record.aiu_amount = 0
            if record.move_id.aiu == 'yes':
                amount_base = 0
                total_aiu = sum(
                    [x.amount_invoice for x in record.move_id.aiu_line_ids])
                subtotal = (record.price_unit * (1 - (record.discount / 100.0))) * record.quantity
                for line in record.move_id.invoice_line_ids:
                    line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                    amount_base += line.quantity * line_discount_price_unit
                if subtotal and amount_base and total_aiu:
                    base_percentage = (subtotal / amount_base) * 100
                    record.aiu_amount = total_aiu * (base_percentage / 100)

    @api.onchange('retention_table_id')
    def _onchange_retention_table_id(self):
        for record in self:
            continue
            record.tax_ids += record.retention_table_id.ica_tax_id
            record.tax_ids += record.retention_table_id.rteica_tax_id
    
    @api.onchange('product_id', 'partner_id')
    def _onchange_tax_partner_id(self):
        for record in self:
            if record.partner_id and record.partner_id.city_id:
                ciiu = self.env['account.tax.retention.table'].search([
                    ('city_id', '=', record.partner_id.city_id.id),
                    ('active', '=', True)
                ], limit=1)
                if ciiu:
                    self.tax_ids += ciiu.ica_tax_id
                    self._onchange_tax_ids()

    def _get_computed_taxes(self):
        taxes_ids = super()._get_computed_taxes()
        if taxes_ids:
            taxes = self.env["account.tax.hierarchy"]._compute_sobreica(taxes_ids, self.product_id, self.partner_id)
            if self.move_id.move_type != 'entry':
                taxes = self.env["account.tax.retention.table"]._compute_reteica(taxes, self.partner_id)
            taxes_ids += taxes
        return taxes_ids

    @api.onchange('tax_ids', 'partner_id')
    def _onchange_tax_ids(self):
        res = super()._onchange_tax_ids()
        for line in self:
            taxes = self.env["account.tax.hierarchy"]._compute_sobreica(line.tax_ids, line.product_id, self.partner_id)
            if self.move_id.move_type != 'entry':
                taxes = self.env["account.tax.retention.table"]._compute_reteica(taxes, line.partner_id)
            line.tax_ids = taxes
        return res

    @api.depends('tax_ids',
                 'currency_id',
                 'partner_id',
                 'analytic_distribution',
                 'balance', 'partner_id',
                 'move_id.partner_id',
                 'price_unit',
                 'quantity')
    def _compute_all_tax(self):
        if self.env.context.get('other_base_tax'):
            context_update = dict(self.env.context)
            context_update.pop('other_base_tax')
            self.env.context = context_update
        for line in self:
            tax_with_other_base = line.move_id._get_dict_tax_other_base()
            context = self.env.context.copy()
            context.update({
                'amount_exclude_aiu': 0
            })
            if line.tax_ids:
                if self.env.context.get('other_base_tax'):
                    context.update({
                        'other_base_tax': self.env.context.get('other_base_tax')
                    })
                elif tax_with_other_base and not self.env.context.get('other_base_tax'):
                    context.update({
                        'other_base_tax': tax_with_other_base
                    })
                    mutable_context = dict(self.env.context)
                    mutable_context.update({'other_base_tax': tax_with_other_base})
                    self.env.context = mutable_context
            sign = line.move_id.direction_sign
            if line.display_type == 'tax':
                line.compute_all_tax = {}
                line.compute_all_tax_dirty = False
                continue
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                amount_currency = sign * (line.price_unit * (1 - line.discount / 100))
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.with_context(context).compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
            )
            rate = line.amount_currency / line.balance if line.balance else 1
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': ((tax['analytic'] or not tax['use_in_tax_closing']) and line.move_id.state == 'draft') and line.analytic_distribution,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                    'move_id': line.move_id.id,
                    'display_type': line.display_type,
                }): {
                    'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
                    'balance': tax['amount'] / rate,
                    'amount_currency': tax['amount'],
                    'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency['taxes']
                if tax['amount']
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
                }

    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_invoice_line_sync'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_invoice_line_sync=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        for line in after:
            if (
                line.display_type == 'product'
                and (not changed('amount_currency') or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(line.price_subtotal + line.aiu_amount)
                if line.amount_currency != amount_currency or line not in before:
                    line.amount_currency = amount_currency
                if line.currency_id == line.company_id.currency_id:
                    line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                and (not changed('balance') or (line not in before and not line.balance))
            ):
                balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                line.balance = balance
        # Since this method is called during the sync, inside of `create`/`write`, these fields
        # already have been computed and marked as so. But this method should re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])

    @api.depends('product_id', 'product_uom_id', 'move_id.tax_ciiu_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note', 'payment_term'):
                continue
            # /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
            if line.product_id or line.account_id.tax_ids or not line.tax_ids or (line.move_id.move_type == 'in_invoice' and line.move_id.tax_ciiu_id):
                line.tax_ids = line._get_computed_taxes()

    def _get_computed_taxes(self):
        tax_ids = super()._get_computed_taxes()
        if self.move_id.move_type == 'in_invoice' and self.move_id.tax_ciiu_id:
            tax_ids += self.move_id.fiscal_position_id.map_tax(self.move_id.tax_ciiu_id)
        return tax_ids
