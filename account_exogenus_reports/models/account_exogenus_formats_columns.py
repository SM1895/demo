# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class AccountExogenusFormatsColumns(models.Model):
    _name = 'account.exogenus.formats.columns'

    name = fields.Char(string='Name')
    description = fields.Char(string='description')
    group_bool = fields.Boolean(
        string="Grouping",
        help="True with column define grouping"
    )
    column_account = fields.Boolean(
        string='Columna with Account',
    )

    exogenus_format_id = fields.Many2one(
        'account.exogenus.formats', string="Format Exogenus", required=True)
    condition_python = fields.Text(
        string="Condition python",
        default="result = object.name")
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    account_colums_ids = fields.One2many(
        'account.exogenus.account.column', 'account_column_id',
        string="Account Columns")

    minior_amount = fields.Boolean(string='Minior Amount')

    type_column = fields.Selection(
        string='Type Column',
        selection=[('data', 'Data'), ('calculated', 'Calculated')]
    )

    def execute_code(self, line, wizard):
        localdict = {
            'line': line,
            'user': self.env.user,
            'wizard': wizard,
            'self': self,
            'obj1': None,
            'obj2': None,
            'obj3': None,
        }
        try:
            exec(self.condition_python, localdict)
            return localdict.get('result', False)
        except Exception as e:
            return "Error %s: value %s" % (self.name, str(e))

    def _get_select(self):
        select = (" SELECT "
                  "case "
                  "when(aeac.nature_account='net') then "
                  " sum(aml.debit-aml.credit) "
                  "when(aeac.nature_account='debit') then sum(aml.debit) "
                  "when(aeac.nature_account='credit') then sum(aml.credit) "
                  "when(aeac.nature_account='balance') then "
                  " COALESCE(sum(aml.balance),0) "
                  "+ sum(aml.debit-aml.credit) "
                  "else 0 end as total "
                  )
        return select

    def _get_from(self):
        sql_from = (" FROM account_move_line aml "
                    " JOIN account_account aa ON aml.account_id=aa.id "
                    " LEFT JOIN account_exogenus_account_column aeac "
                    " ON aeac.account_id = aa.id ")
        return sql_from

    def _get_where(self, params):
        sql_where = (" WHERE aml.partner_id = %(partner_id)s "
                     " AND aml.date>=%(date_from)s AND aml.date<=%(date_to)s "
                     " AND aeac.account_column_id = %(columns_id)s "
                     )
        if params.get('account_ids', False):
            sql_where += " AND aml.account_id in %(account_ids)s "
        return sql_where

    def _get_group(self):
        group = (" GROUP BY aeac.nature_account ")
        return group

    def _get_account_column(self):
        account_ids = []
        for account in self.account_colums_ids:
            account_ids.append(account.account_id.id)
        return account_ids

    def _get_total_aml_by_column(self, params):
        result = ''
        account_ids = self._get_account_column()
        if len(account_ids) > 0:
            params['account_ids'] = tuple(account_ids)
            params['columns_id'] = self.id
            select = self._get_select()
            sql_from = self._get_from()
            sql_where = self._get_where(params)
            sql_group = self._get_group()
            self.env.cr.execute(select+sql_from+sql_where+sql_group, params)
            total_column = self.env.cr.dictfetchall()
            result = abs(total_column[0]['total']) if total_column else 0
        return result

    def action_select_account(self):
        return {
            'name': _('select account'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.column.account.wizard',
            'target': 'new',
            'context': {'default_acount_exogenus_format_column_id': self.id}
        }


class AccountExogenusAccountColumn(models.Model):
    _name = "account.exogenus.account.column"

    name = fields.Char(string='Name', required=True,
                       related="account_id.code")
    account_column_id = fields.Many2one(
        'account.exogenus.formats.columns', string='Column',
        ondelete="cascade", index=True, auto_join=True, store=True)
    account_id = fields.Many2one(
        'account.account', string="Account")
    nature_account = fields.Selection([
        ("net", "net"),
        ("debit", "debit"),
        ("credit", "credit"),
        ("balance", "balance")],
        default='net',
        string=_("Nature account")
    )
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)


class AccountExogenusFormatsColumnsSequence(models.Model):
    _name = 'account.exogenus.formats.columns.sequence'

    exogenus_format_id = fields.Many2one(
        'account.exogenus.formats',
        string="Format")
    account_format_column_id = fields.Many2one(
        'account.exogenus.formats.columns',
        string="Column")
    sequence = fields.Integer(string="Sequence")
