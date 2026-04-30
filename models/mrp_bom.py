from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    skip_phantom_check = fields.Boolean(
        string="Bypass anti-fantome",
        default=False,
        help="Si coche, les MO de cette nomenclature ne sont pas controlees par "
             "sopromer_mrp_no_phantom. A reserver aux deconstructions ou recettes "
             "ou la sortie peut legitimement depasser l'entree.",
    )
