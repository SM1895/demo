# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import format_date
import copy
import binascii
import struct
import time
import itertools
from collections import defaultdict

MAX_NAME_LENGTH = 50


class assets_report(models.AbstractModel):

    _name = 'account.assets.report.extended'
    _inherit = 'account.assets.report'
    _description = 'Account Assets Report'

    def get_header(self, options):
        start_date = format_date(self.env, options['date']['date_from'])
        end_date = format_date(self.env, options['date']['date_to'])
        return [
            [
                {'name': ''},
                {'name': _('Caracteristics'), 'colspan': 5},
                {'name': _('Datos Activo'), 'colspan': 4},
                {'name': _('Depreciation'), 'colspan': 4},
                {'name': _('Fiscal Depreciation'), 'colspan': 14},
                {'name': _('Book Value')},
            ],
            [
                {'name': ''},  # Description
                {'name': _('Acquisition Date'), 'class': 'text-center'}, # Caracteristics
                {'name': _('First Depreciation'), 'class': 'text-center'},
                {'name': _('Method'), 'class': 'text-center'},
                {'name': _('Rate'), 'class': 'number', 'title': _('In percent.<br>For a linear method, the depreciation rate is computed per year.<br>For a degressive method, it is the degressive factor'), 'data-toggle': 'tooltip'},
                {'name': start_date, 'class': 'number'},  # Assets
                {'name': _('+'), 'class': 'number'},
                {'name': _('-'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': start_date, 'class': 'number'},  # Depreciation
                {'name': _('+'), 'class': 'number'},
                {'name': _('-'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': _('Depreciación Acumulada'), 'class': 'text-center'}, # Depreciacion Fiscal
                {'name': _('Enero'), 'class': 'number'},
                {'name': _('Febrero'), 'class': 'number'},
                {'name': _('Marzo'), 'class': 'number'},
                {'name': _('Abril'), 'class': 'number'},
                {'name': _('Mayo'), 'class': 'number'},
                {'name': _('Junio'), 'class': 'number'},
                {'name': _('Julio'), 'class': 'number'},
                {'name': _('Agosto'), 'class': 'number'},
                {'name': _('Septiembre'), 'class': 'number'},
                {'name': _('Octubre'), 'class': 'number'},
                {'name': _('Noviembre'), 'class': 'number'},
                {'name': _('Diciembre'), 'class': 'number'},
                {'name': _('Total depreciaciones'), 'class': 'number'},
                {'name': '', 'class': 'number'},  # Gross
            ],
        ]

    def _get_lines(self, options, line_id=None):
        options['self'] = self
        lines = []
        total = [0] * 9
        total_depreciation = [0] * 13
        asset_lines = self._get_assets_lines(options)
        asset_lines_niff = self._get_assets_niff_lines(options)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in asset_lines:
            if al['parent_id']:
                children_lines[al['parent_id']] += [al]
            else:
                parent_lines += [al]
        for al in asset_lines_niff:
            if al['parent_id']:
                children_lines[al['parent_id']] += [al]
            else:
                parent_lines += [al]
        for al in parent_lines:
            if al['asset_method'] == 'linear' and al['asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                asset_depreciation_rate = ('{:.2f} %').format((100.0 / al['asset_method_number']) * (12 / int(al['asset_method_period'])))
            elif al['asset_method'] == 'linear':
                asset_depreciation_rate = ('{:.2f} %').format(0.0)
            else:
                asset_depreciation_rate = ('{:.2f} %').format(float(al['asset_method_progress_factor']) * 100)

            depreciation_opening = al['depreciated_start'] - al['depreciation']
            depreciation_closing = al['depreciated_end']
            depreciation_minus = 0.0

            opening = (al['asset_acquisition_date'] or al['asset_date']) < fields.Date.to_date(options['date']['date_from'])
            asset_opening = al['asset_original_value'] if opening else 0.0
            asset_add = 0.0 if opening else al['asset_original_value']
            asset_minus = 0.0

            for child in children_lines[al['asset_id']]:
                depreciation_opening += child['depreciated_start'] - child['depreciation']
                depreciation_closing += child['depreciated_end']

                opening = (child['asset_acquisition_date'] or child['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                asset_opening += child['asset_original_value'] if opening else 0.0
                asset_add += 0.0 if opening else child['asset_original_value']

            depreciation_add = depreciation_closing - depreciation_opening
            asset_closing = asset_opening + asset_add

            if al['asset_state'] == 'close' and al['asset_disposal_date'] and al['asset_disposal_date'] < fields.Date.to_date(options['date']['date_to']):
                depreciation_minus = depreciation_closing
                depreciation_closing = 0.0
                depreciation_opening += depreciation_add
                depreciation_add = 0
                asset_minus = asset_closing
                asset_closing = 0.0

            if al['asset_id']:
                asset = self.env['account.asset'].browse(al['asset_id'])
                year_from = fields.Date.to_date(options['date']['date_from']).year
                year_to = fields.Date.to_date(options['date']['date_to']).year
                moves = asset.depreciation_move_ids.filtered(lambda x: x.asset_clasification=='FISCAL' and x.date >= fields.Date.to_date(options['date']['date_from']) and x.date <= fields.Date.to_date(options['date']['date_to']))
                times = 0
                total_amounts_year = []
                total_depreciation_year = []
                total_amounts_month = [0]*13
                for year in range(year_from,year_to+1):
                    times += 1
                    for month in range(1,13):
                        for move in moves:
                            if move.date.year == year and move.date.month == month:
                                total_amounts_month[month-1] =move.amount_total
                    total_amounts_month[12] = sum(total_amounts_month) 
                    copy = total_amounts_month.copy() 
                    total_amounts_year.append(copy)
                    total_amounts_month = [0]*13
                    # datos para la depreciacion acumulada
                    last_year = year - 1
                    last_depreciation = asset.depreciation_move_ids.filtered(lambda x: x.asset_clasification=='FISCAL' and x.date.year == last_year and x.date.month == 12).asset_depreciated_value
                    total_depreciation_year.append(last_depreciation)

            asset_gross = asset_closing - depreciation_closing

            total = [x + y for x, y in zip(total, [asset_opening, asset_add, asset_minus, asset_closing, depreciation_opening, depreciation_add, depreciation_minus, depreciation_closing, asset_gross])]

            for time in range(0,times):
                total_depreciation = [x + y for x, y in zip(total_depreciation, [total_amounts_year[time][0], total_amounts_year[time][1], total_amounts_year[time][2], total_amounts_year[time][3], 
                                    total_amounts_year[time][4], total_amounts_year[time][5], total_amounts_year[time][6], total_amounts_year[time][7], total_amounts_year[time][8], total_amounts_year[time][9], 
                                    total_amounts_year[time][10], total_amounts_year[time][11], total_amounts_year[time][12]])]

            id = "_".join([self._get_account_group(al['account_code'])[0], str(al['asset_id'])])
            name = str(al['asset_name'])
            for time in range(0,times):
                line = {
                    'id': id,
                    'level': 1,
                    'name': name if len(name) < MAX_NAME_LENGTH else name[:MAX_NAME_LENGTH - 2] + '...',
                    'columns': [
                        {'name': al['asset_acquisition_date'] and format_date(self.env, al['asset_acquisition_date']) or '', 'no_format_name': ''},  # Caracteristics
                        {'name': al['asset_date'] and format_date(self.env, al['asset_date']) or '', 'no_format_name': ''},
                        {'name': (al['asset_method'] == 'linear' and _('Linear')) or (al['asset_method'] == 'degressive' and _('Degressive')) or _('Accelerated'), 'no_format_name': ''},
                        {'name': asset_depreciation_rate, 'no_format_name': ''},
                        {'name': self.format_value(asset_opening), 'no_format_name': asset_opening},  # Assets
                        {'name': self.format_value(asset_add), 'no_format_name': asset_add},
                        {'name': self.format_value(asset_minus), 'no_format_name': asset_minus},
                        {'name': self.format_value(asset_closing), 'no_format_name': asset_closing},
                        {'name': self.format_value(depreciation_opening), 'no_format_name': depreciation_opening},  # Depreciation
                        {'name': self.format_value(depreciation_add), 'no_format_name': depreciation_add},
                        {'name': self.format_value(depreciation_minus), 'no_format_name': depreciation_minus},
                        {'name': self.format_value(depreciation_closing), 'no_format_name': depreciation_closing},
                        {'name': self.format_value(total_depreciation_year[time]), 'no_format_name': total_depreciation_year[time]}, #depreciacion Fiscal
                        {'name': self.format_value(total_amounts_year[time][0]), 'no_format_name': total_amounts_year[time][0]}, 
                        {'name': self.format_value(total_amounts_year[time][1]), 'no_format_name': total_amounts_year[time][1]},
                        {'name': self.format_value(total_amounts_year[time][2]), 'no_format_name': total_amounts_year[time][2]},
                        {'name': self.format_value(total_amounts_year[time][3]), 'no_format_name': total_amounts_year[time][3]},
                        {'name': self.format_value(total_amounts_year[time][4]), 'no_format_name': total_amounts_year[time][4]},
                        {'name': self.format_value(total_amounts_year[time][5]), 'no_format_name': total_amounts_year[time][5]},
                        {'name': self.format_value(total_amounts_year[time][6]), 'no_format_name': total_amounts_year[time][6]},
                        {'name': self.format_value(total_amounts_year[time][7]), 'no_format_name': total_amounts_year[time][7]},
                        {'name': self.format_value(total_amounts_year[time][8]), 'no_format_name': total_amounts_year[time][8]},
                        {'name': self.format_value(total_amounts_year[time][9]), 'no_format_name': total_amounts_year[time][9]},
                        {'name': self.format_value(total_amounts_year[time][10]), 'no_format_name': total_amounts_year[time][10]},
                        {'name': self.format_value(total_amounts_year[time][11]), 'no_format_name': total_amounts_year[time][11]},
                        {'name': self.format_value(total_amounts_year[time][12]), 'no_format_name': total_amounts_year[time][12]},
                        {'name': self.format_value(asset_gross), 'no_format_name': asset_gross},  # Gross
                    ],
                    'unfoldable': False,
                    'unfolded': False,
                    'caret_options': 'account.asset.line',
                    'account_id': al['account_id']
                }
                if len(name) >= MAX_NAME_LENGTH:
                    line.update({'title_hover': name})
                lines.append(line)
        lines.append({
            'id': 'total',
            'level': 0,
            'name': _('Total'),
            'columns': [
                {'name': ''},  # Caracteristics
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': self.format_value(total[0])},  # Assets
                {'name': self.format_value(total[1])},
                {'name': self.format_value(total[2])},
                {'name': self.format_value(total[3])},
                {'name': self.format_value(total[4])},  # Depreciation
                {'name': self.format_value(total[5])},
                {'name': self.format_value(total[6])},
                {'name': self.format_value(total[7])},
                {'name': self.format_value(total_depreciation[0])}, # Depreciacion Fiscal
                {'name': self.format_value(total_depreciation[1])},
                {'name': self.format_value(total_depreciation[2])},
                {'name': self.format_value(total_depreciation[3])},
                {'name': self.format_value(total_depreciation[4])},
                {'name': self.format_value(total_depreciation[5])},
                {'name': self.format_value(total_depreciation[6])},
                {'name': self.format_value(total_depreciation[7])},
                {'name': self.format_value(total_depreciation[8])},
                {'name': self.format_value(total_depreciation[9])},
                {'name': self.format_value(total_depreciation[10])},
                {'name': self.format_value(total_depreciation[11])},
                {'name': self.format_value(total_depreciation[12])},
                {'name': self.format_value(total[8])},  # Gross
            ],
            'unfoldable': False,
            'unfolded': False,
        })
        return lines

    


    def _get_assets_niff_lines(self, options):
        "Get the data from the database"
        where_account_move = " AND state != 'cancel'"
        if not options.get('all_entries'):
            where_account_move = " AND state = 'posted'"

        sql = """
                -- remove all the moves that have been reversed from the search
                CREATE TEMPORARY TABLE IF NOT EXISTS temp_account_move () INHERITS (account_move) ON COMMIT DROP;
                INSERT INTO temp_account_move SELECT move.*
                FROM ONLY account_move move
                LEFT JOIN ONLY account_move reversal ON reversal.reversed_entry_id = move.id
                WHERE reversal.id IS NULL AND move.asset_id IS NOT NULL AND move.company_id in %(company_ids)s;

                SELECT asset.id as asset_id,
                       asset.parent_id as parent_id,
                       asset.name as asset_name,
                       asset.value_residual_niff as asset_value,
                       asset.original_value_niff as asset_original_value,
                       asset.first_depreciation_date_niff as asset_date,
                       asset.disposal_date as asset_disposal_date,
                       asset.acquisition_date_niff as asset_acquisition_date,
                       asset.method_niff as asset_method,
                       (SELECT COUNT(*) FROM temp_account_move WHERE asset_id = asset.id AND asset_value_change != 't') as asset_method_number,
                       asset.method_period_niff as asset_method_period,
                       asset.method_progress_factor_niff as asset_method_progress_factor,
                       asset.state as asset_state,
                       account.code as account_code,
                       account.name as account_name,
                       account.id as account_id,
                       COALESCE(first_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_start,
                       COALESCE(first_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_start,
                       COALESCE(last_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_end,
                       COALESCE(last_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_end,
                       COALESCE(first_move.amount_total, 0.0) as depreciation
                FROM account_asset as asset
                LEFT JOIN account_account as account ON asset.account_asset_id_niff = account.id
                LEFT OUTER JOIN (SELECT MIN(date) as date, asset_id FROM temp_account_move WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move} GROUP BY asset_id) min_date_in ON min_date_in.asset_id = asset.id
                LEFT OUTER JOIN (SELECT MAX(date) as date, asset_id FROM temp_account_move WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move} GROUP BY asset_id) max_date_in ON max_date_in.asset_id = asset.id
                LEFT OUTER JOIN (SELECT MAX(date) as date, asset_id FROM temp_account_move WHERE date <= %(date_from)s {where_account_move} GROUP BY asset_id) max_date_before ON max_date_before.asset_id = asset.id
                LEFT OUTER JOIN temp_account_move as first_move ON first_move.id = (SELECT m.id FROM temp_account_move m WHERE m.asset_id = asset.id AND m.date = min_date_in.date and m.asset_clasification = 'NIFF' ORDER BY m.id ASC LIMIT 1)
                LEFT OUTER JOIN temp_account_move as last_move ON last_move.id = (SELECT m.id FROM temp_account_move m WHERE m.asset_id = asset.id AND m.date = max_date_in.date and m.asset_clasification = 'NIFF' ORDER BY m.id DESC LIMIT 1)
                LEFT OUTER JOIN temp_account_move as move_before ON move_before.id = (SELECT m.id FROM temp_account_move m WHERE m.asset_id = asset.id AND m.date = max_date_before.date and m.asset_clasification = 'NIFF' ORDER BY m.id DESC LIMIT 1)
                WHERE asset.company_id in %(company_ids)s
                AND asset.acquisition_date_niff <= %(date_to)s
                AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                AND asset.state not in ('model', 'draft')
                AND asset.asset_type = 'purchase'
                AND asset.active = 't'

                ORDER BY account.code;
            """.format(where_account_move=where_account_move)

        date_to = options['date']['date_to']
        date_from = options['date']['date_from']
        company_ids = tuple(t['id'] for t in self._get_options_companies(options))

        self.flush()
        self.env.cr.execute(sql, {'date_to': date_to, 'date_from': date_from, 'company_ids': company_ids})
        results = self.env.cr.dictfetchall()
        self.env.cr.execute("DROP TABLE temp_account_move")  # Because tests are run in the same transaction, we need to clean here the SQL INHERITS
        return results

    @api.model
    def _create_hierarchy_asset_extended(self, lines, options):
        
        new_lines = []
        parent_id = ''
        for line in lines:
            if line.get('level') == 1:
                parent_id = line.get('id')
                new_lines.append(line)
                new_dict_line = line.copy()
                asset_done = []
            elif line.get('parent_id') == parent_id and line.get('level')==2:
                if line.get('name') not in asset_done:
                    asset_done.append(line.get('name'))
                    new_dict = new_dict_line.copy()
                    name = line.get('name')
                    new_dict_id = parent_id + '_'  + name
                    new_dict['id'] = new_dict_id
                    new_dict['level'] = 2
                    new_dict['name'] = name
                    new_dict['parent_id'] = parent_id
                    new_dict['tittle_hover'] = name
                    new_lines.append(new_dict)
                line['level'] = 3
                line['parent_id'] = new_dict_id
                new_lines.append(line)
        return new_lines


    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Check the security before updating the context to make sure the options are safe.
        self._check_report_security(options)

        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates()
        report_manager = self._get_report_manager(options)
        report = {'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,}
        lines = self._get_lines(options, line_id=line_id)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
            lines = self._create_hierarchy_asset_extended(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        rcontext = {'report': report,
                    'lines': {'columns_header': self.get_header(options), 'lines': lines},
                    'options': options,
                    'context': self.env.context,
                    'model': self,
                }
        if additional_context and type(additional_context) == dict:
            rcontext.update(additional_context)
        if self.env.context.get('analytic_account_ids'):
            rcontext['options']['analytic_account_ids'] = [
                {'id': acc.id, 'name': acc.name} for acc in self.env.context['analytic_account_ids']
            ]

        render_template = templates.get('main_template', 'account_reports.main_template')
        if line_id is not None:
            render_template = templates.get('line_template', 'account_reports.line_template')
        html = self.env['ir.ui.view'].render_template(
            render_template,
            values=dict(rcontext),
        )
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
        return html