import logging

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # ------------------------------------------------------------------
    # HOOK PRIORITAIRE — Check stock dispo a la confirmation MO
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Bloque la confirmation d'une MO si le stock matiere est insuffisant.

        Ce hook est prioritaire : il empeche la creation meme du picking
        de consommation tant que la matiere n'est pas physiquement presente.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        check_at_confirm = ICP.get_param(
            'sopromer_mrp_no_phantom.stock_check_at_confirm', 'True',
        ) == 'True'
        if check_at_confirm:
            for production in self:
                if production.bom_id and production.bom_id.skip_phantom_check:
                    _logger.warning(
                        "sopromer_mrp_no_phantom: BoM %s (id=%s) bypass active "
                        "sur MO %s — skip stock check at confirm",
                        production.bom_id.display_name,
                        production.bom_id.id,
                        production.name,
                    )
                    continue
                production._sopromer_check_stock_available()
        return super().action_confirm()

    def _sopromer_check_stock_available(self):
        """Pour chaque move_raw, verifie que le stock libre suffit.

        Stock libre = quantity - reserved_quantity sur les quants du
        location_id du move (matiere physiquement disponible et non
        deja reservee par un autre MO/picking).
        """
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure',
        )
        Quant = self.env['stock.quant'].sudo()

        for move in self.move_raw_ids:
            # Skip moves a qty zero (rien a verifier) ou en cancel
            if float_is_zero(move.product_uom_qty, precision_digits=precision):
                continue
            if move.state == 'cancel':
                continue

            # Calcul stock libre sur le location source du move
            quants = Quant.search([
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', move.location_id.id),
            ])
            qty_on_hand = sum(quants.mapped('quantity'))
            qty_reserved = sum(quants.mapped('reserved_quantity'))
            qty_available = qty_on_hand - qty_reserved

            # Conversion qty requise dans l'UoM du produit (uom interne quant)
            product_uom = move.product_id.uom_id
            if move.product_uom and move.product_uom != product_uom:
                qty_required = move.product_uom._compute_quantity(
                    move.product_uom_qty, product_uom,
                )
            else:
                qty_required = move.product_uom_qty

            if float_compare(
                qty_available, qty_required, precision_digits=precision,
            ) < 0:
                missing = qty_required - qty_available
                _logger.info(
                    "sopromer_mrp_no_phantom: BLOCAGE confirm MO %s — "
                    "composant %s @ %s : dispo=%.3f %s, requis=%.3f %s, manque=%.3f %s",
                    self.name,
                    move.product_id.display_name,
                    move.location_id.complete_name,
                    qty_available, product_uom.name,
                    qty_required, product_uom.name,
                    missing, product_uom.name,
                )
                raise UserError(_(
                    "Stock matiere insuffisant — confirmation MO impossible.\n\n"
                    "Composant : %(product)s\n"
                    "Qty requise : %(required).3f %(uom)s\n"
                    "Stock disponible @ %(location)s : %(available).3f %(uom)s\n"
                    "Manque : %(missing).3f %(uom)s\n\n"
                    "Action : effectuer la reception ou l'inventaire de la "
                    "matiere premiere avant de confirmer cette fabrication.",
                    product=move.product_id.display_name,
                    required=qty_required,
                    uom=product_uom.name,
                    location=move.location_id.complete_name or move.location_id.name,
                    available=qty_available,
                    missing=missing,
                ))

    # ------------------------------------------------------------------
    # HOOK SECONDAIRE — Filet de securite a button_mark_done
    # (garde au cas ou le stock devient indisponible entre confirm et done :
    # ex. autre MO consomme la matiere entre-temps)
    # ------------------------------------------------------------------
    def button_mark_done(self):
        for production in self:
            production._sopromer_check_no_phantom()
        return super().button_mark_done()

    def _sopromer_check_no_phantom(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()

        if self.bom_id and self.bom_id.skip_phantom_check:
            _logger.warning(
                "sopromer_mrp_no_phantom: BoM %s (id=%s) bypass active sur MO %s",
                self.bom_id.display_name, self.bom_id.id, self.name,
            )
            return

        block_zero = ICP.get_param(
            'sopromer_mrp_no_phantom.block_zero_consumption', 'True',
        ) == 'True'
        if block_zero:
            self._sopromer_check_zero_consumption()

        mass_balance = ICP.get_param(
            'sopromer_mrp_no_phantom.mass_balance_enabled', 'False',
        ) == 'True'
        if mass_balance:
            tolerance = float(ICP.get_param(
                'sopromer_mrp_no_phantom.mass_balance_tolerance', '5.0',
            ))
            self._sopromer_check_mass_balance(tolerance)

    def _sopromer_check_zero_consumption(self):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move in self.move_raw_ids:
            if float_is_zero(move.product_uom_qty, precision_digits=precision):
                continue
            if move.state == 'cancel':
                raise UserError(_(
                    "Composant %(product)s : move annule alors que la qty theorique "
                    "etait %(qty)s %(uom)s.\n"
                    "Reactiver le move ou reduire la qty theorique BoM avant validation.",
                    product=move.product_id.display_name,
                    qty=move.product_uom_qty,
                    uom=move.product_uom.name,
                ))
            if float_is_zero(move.quantity, precision_digits=precision):
                raise UserError(_(
                    "Composant %(product)s : qty theorique %(qty)s %(uom)s, "
                    "qty consommee 0.\n"
                    "Saisir la consommation reelle ou reduire la qty theorique BoM "
                    "avant validation.",
                    product=move.product_id.display_name,
                    qty=move.product_uom_qty,
                    uom=move.product_uom.name,
                ))

    def _sopromer_check_mass_balance(self, tolerance):
        self.ensure_one()
        kg_uom = self.env.ref('uom.product_uom_kgm', raise_if_not_found=False)
        if not kg_uom:
            _logger.warning(
                "sopromer_mrp_no_phantom: UoM kg introuvable, skip mass balance MO %s",
                self.name,
            )
            return

        total_in = self._sopromer_sum_kg(self.move_raw_ids, kg_uom)
        total_out = self._sopromer_sum_kg(self.move_finished_ids, kg_uom)

        if total_in <= 0:
            return

        max_out = total_in * (1 + tolerance / 100.0)
        if float_compare(total_out, max_out, precision_digits=3) > 0:
            raise UserError(_(
                "Conservation masse violee sur %(name)s : sortie %(out).3f kg > "
                "entree %(in).3f kg + tolerance %(tol).1f%%.\n"
                "Verifier les quantites produites ou ajuster la tolerance dans "
                "Parametres > Fabrication.",
                name=self.name,
                out=total_out,
                **{'in': total_in},
                tol=tolerance,
            ))

    def _sopromer_sum_kg(self, moves, kg_uom):
        total = 0.0
        for move in moves:
            if move.state != 'done':
                continue
            uom = move.product_uom
            if not uom or uom.category_id != kg_uom.category_id:
                _logger.warning(
                    "sopromer_mrp_no_phantom: UoM %s incompatible kg, skip move %s",
                    uom.name if uom else 'N/A', move.id,
                )
                continue
            try:
                qty_kg = uom._compute_quantity(move.quantity, kg_uom)
            except Exception as exc:
                _logger.warning(
                    "sopromer_mrp_no_phantom: conversion kg echouee move %s: %s",
                    move.id, exc,
                )
                continue
            total += qty_kg
        return total
