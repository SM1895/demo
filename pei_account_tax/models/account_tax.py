from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['account.tax', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nombre del Impuesto',
        tracking=True
    )
    active = fields.Boolean(
        string='Activo',
        help="Establece activo a falso para ocultar el impuesto sin eliminarlo.",
        tracking=True
    )
    amount = fields.Float(
        string='Importe',
        tracking=True
    )
    type_tax_use = fields.Selection(
        string='Tipo de Impuesto',
        help=("Determina dónde el impuesto puede ser seleccionado. Nota: \"Ninguno\" "
              "significa que un impuesto no puede ser usado por sí mismo, sin embargo aún "
              "puede ser usado en un grupo. \"Ajuste\" es usado para realizar un ajuste de "
              "impuesto. "),
        tracking=True
    )
    amount_type = fields.Selection(
        string='Cálculo de Impuestos',
        help=("\n"
              "Grupo de impuestos: El impuesto es un conjunto de sub impuestos.\n"
              " - Fijo: El importe del impuesto permanece igual independientemente del precio.\n"
              " - Porcentaje del precio: el importe del impuesto es un % del precio:\n"
              " Por ejemplo, 100 * (1 + 10%) = 110 (sin precio incluido)\n"
              "por ejemplo, 110 / (1 + 10%) = 100 (precio incluido)\n"
              "- Porcentaje del Precio con Impuesto Incluido: El importe del impuesto es una división del precio:\n"
              "Por ejemplo, 180 / (1 - 10%) = 200 (sin precio incluido)\n"
              "Por ejemplo, 200 * (1-10%) =  180  (precio incluido)\n"
              "        "),
        tracking=True
    )
    tax_scope = fields.Selection(
        string='Ámbito del Impuesto',
        help=("Restringir el uso de impuestos a un tipo de producto."),
        tracking=True
    )
    rel_amount = fields.Float(
        string='Related Amount'
    )
    rel_name = fields.Char(
        string='Related Name',
    )
    on_tax_ica = fields.Boolean(
        string='Sobretasa ICA',
        default=False
    )
    first_ica_id = fields.Many2one(
        comodel_name='account.tax',
        string='Sobre Impuesto ICA 1'
    )
    second_ica_id = fields.Many2one(
        comodel_name='account.tax',
        string='Sobre Impuesto ICA 2'
    )
    third_ica_id = fields.Many2one(
        comodel_name='account.tax',
        string='Sobre Impuesto ICA 3'
    )
    hierarchy1_id = fields.Many2one(
        comodel_name='account.tax.hierarchy',
        string='Jerarquía 1'
    )
    hierarchy2_id = fields.Many2one(
        comodel_name='account.tax.hierarchy',
        string='Jerarquía 2'
    )
    hierarchy3_id = fields.Many2one(
        comodel_name='account.tax.hierarchy',
        string='Jerarquía 3'
    )
    inherit_analytic = fields.Boolean(
        string='¿Hereda Cuentas Analíticas?',
        default=False
    )
    utility_base = fields.Boolean(
        string='Cálculo AIU en Base a Concepto',
        help='Esta Configuración solo se tomará en cuenta cuando el cálculo AIU sea de tipo Obra Civil'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'rel_amount' in val:
                self._validate_amount(val.get('rel_amount'))
            if val.get('rel_name'):
                self._validate_name(val.get('rel_name'))
        res = super().create(vals_list)
        if 'on_tax_ica' in val:
            self._validate_on_tax_ica(val)
        return res

    def write(self, vals):
        if 'rel_amount' in vals:
            self._validate_amount(vals.get('rel_amount'))
        if vals.get('rel_name'):
            self._validate_name(vals.get('rel_name'), True)
        if 'on_tax_ica' in vals:
            if vals['on_tax_ica'] == self.on_tax_ica:
                del vals['on_tax_ica']
        res = super().write(vals)
        if 'on_tax_ica' in vals:
            self._validate_on_tax_ica(vals)
        return res

    def _validate_amount(self, amount):
        if amount == 0:
            return
            raise ValidationError('No se puede crear un '
                                  'impuesto con importe en 0.')

    def _validate_name(self, name, write=False):
        domain_search = [
            ('name', '=', name),
            ('company_id', '=', self.env.company.id)
        ]
        if write:
            domain_search.append(('id', '!=', self.id))
        if self.env['account.tax'].search(domain_search):
            raise ValidationError('El nombre asignado al impuesto'
                                  ' ya esta asociado a otro.')

    def _validate_on_tax_ica(self, vals):
        for record in self:
            if record.hierarchy1_id:
                raise ValidationError(
                    'No se puede desmarcar la opción, ya fueron creadas las configuraciones de jerarquía.')
            if record.first_ica_id.id == self.id:
                raise ValidationError(
                    'No se puede establecer el impuesto sobreica igual al actual impuesto.')
            if (record.first_ica_id.id in [record.second_ica_id.id or -1, record.third_ica_id.id or -1] or
                    record.second_ica_id.id in [record.first_ica_id.id or -1, record.third_ica_id.id or -1] or 
                    record.third_ica_id.id in [record.first_ica_id.id or -1, record.second_ica_id.id or -1]):
                raise ValidationError('Los impuestos sobreica no pueden ser los mismos')
            taxes = record.first_ica_id.id + record.second_ica_id.id + record.third_ica_id.id
            if record.first_ica_id.id:
                hierarchy = self.env['account.tax.hierarchy'].create({
                    'parent_tax_id': record.id,
                    'child_tax_id': record.first_ica_id.id,
                    'ica_child_tax_id': record.first_ica_id.id,
                    'method': 'sobreica',
                    'detailed_type': False
                })
                record.hierarchy1_id = hierarchy
            if record.second_ica_id.id:
                hierarchy = self.env['account.tax.hierarchy'].create({
                    'parent_tax_id': record.id,
                    'child_tax_id': record.second_ica_id.id,
                    'ica_child_tax_id': record.second_ica_id.id,
                    'method': 'sobreica',
                    'detailed_type': False
                })
                record.hierarchy2_id = hierarchy
            if record.third_ica_id.id:
                hierarchy = self.env['account.tax.hierarchy'].create({
                    'parent_tax_id': record.id,
                    'child_tax_id': record.third_ica_id.id,
                    'ica_child_tax_id': record.third_ica_id.id,
                    'method': 'sobreica',
                    'detailed_type': False
                })
                record.hierarchy3_id = hierarchy
    
    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
        self.ensure_one()
        
        amount_untaxed_base = self.env.context.get('document_base') if 'document_base' in self.env.context else False
        if self.tax_apply_base and amount_untaxed_base:
            if self.tax_apply_base_condition == 'greater' and amount_untaxed_base <= self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'greater or equal' and amount_untaxed_base < self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'smaller' and amount_untaxed_base >= self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'less or equal' and amount_untaxed_base > self.tax_apply_base_value:
                return 0.0
            if self.tax_apply_base_condition == 'equal' and self.tax_apply_base_value != amount_untaxed_base:
                return 0.0

        tax_id = self.id if isinstance(self.id, int) else self.id.origin
        taxc = self.env["account.tax.hierarchy"].search([("ica_child_tax_id", "=", tax_id), ("method", "=", "sobreica")], limit=1)
        if taxc:
            parent = taxc.parent_tax_id._compute_amount(base_amount, price_unit, quantity, product, partner, fixed_multiplicator)
            return parent * self.amount/100

        taxes_to_exclude = []
        if self.env.context.get('other_base_tax'):
            other_taxes = self.env.context.get('other_base_tax')
            for tax, vals in other_taxes.items():
                if tax in self._ids:
                    taxes_to_exclude.append(tax)
                    if vals['remaining'] != 0:
                        vals['remaining'] = 0
                        base_amount = vals['base']
                        quantity = 1
                    else:
                        base_amount = vals['remaining']
                    if self.env.context.get('parent_tax', 0) == tax:
                        base_amount = vals['base_other_tax']
                        vals['base_other_tax'] = 0
        if self.env.context.get('amount_exclude_aiu') and self.id not in taxes_to_exclude:
            base_amount -= self.env.context.get('amount_exclude_aiu')
        return super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner, fixed_multiplicator)
    
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):
        if product and product._name == 'product.template':
            product = product.product_variant_id
        Hierarchy = self.env["account.tax.hierarchy"]
        orphan = self & Hierarchy.search([("method", "=", "sobreica")]).filtered(lambda h: h.parent_tax_id.id not in self.ids).child_tax_id
        if orphan:
            self = self - orphan
        return super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund=is_refund, handle_price_include=handle_price_include, include_caba_tags=include_caba_tags, fixed_multiplicator=fixed_multiplicator)

    @api.onchange('amount')
    def _onchange_amount(self):
        for record in self:
            record.rel_amount = record.amount
    
    @api.onchange('name')
    def _onchange_name(self):
        for record in self:
            if record.name:
                record.rel_name = record.name
            else:
                record.rel_name = False
