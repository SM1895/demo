# -*- coding: utf-8 -*-

from . import models
from . import tests
from odoo.exceptions import ValidationError,UserError


def l10n_co_partner_pre_init_hook(cr):
    query = '''SELECT id, vat, l10n_latam_identification_type_id,name 
    FROM (  SELECT  *, 
                    COUNT(*) OVER(PARTITION BY vat) N
            FROM res_partner where parent_id is null and vat is not null ) as A
    WHERE N > 1 '''
    cr.execute(query)
    contacts = list(line for line in cr.fetchall())
    if contacts:
        for contact in contacts:
            vat_initial = contacts[0][1]
            repetidos = [x for x in contacts if x[1] == vat_initial]
            for i in range ( len(repetidos)):
                lista = repetidos[:]
                lista.remove(repetidos[i])
                for k in range ( len(lista)):
                    if repetidos[i][2] == lista[k][2]:
                        raise ValidationError("El contacto %s(%s), esta repetido con %s(%s)  "% (lista[k][3],lista[k][0],repetidos[i][3] ,repetidos[i][0] ) )
                contacts.remove(repetidos[i])
