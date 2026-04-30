from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sopromer_stock_check_at_confirm = fields.Boolean(
        string="Bloquer confirmation MO si stock matiere insuffisant",
        config_parameter='sopromer_mrp_no_phantom.stock_check_at_confirm',
        default=True,
    )
    sopromer_block_zero_consumption = fields.Boolean(
        string="Bloquer fabrications avec composant non consomme",
        config_parameter='sopromer_mrp_no_phantom.block_zero_consumption',
        default=True,
    )
    sopromer_mass_balance_enabled = fields.Boolean(
        string="Verifier conservation de masse",
        config_parameter='sopromer_mrp_no_phantom.mass_balance_enabled',
        default=False,
    )
    sopromer_mass_balance_tolerance = fields.Float(
        string="Tolerance masse (%)",
        config_parameter='sopromer_mrp_no_phantom.mass_balance_tolerance',
        default=5.0,
    )
