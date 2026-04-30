# SOPROMER MRP No Phantom

Module Odoo 18 qui empeche structurellement la creation de stock fantome via les fabrications MRP.

## Contexte

Suite a l'incident MO/00457 du 29/04/2026 (2758 kg de sous-produits crees sans matiere premiere deduite), ce module ajoute deux garde-fous au-dessus du mode `consumption` natif des nomenclatures.

## Comportement

### Hook 1 (par defaut ON) - Blocage qty consommee 0
A la validation d'une MO, pour chaque `move_raw_ids` :
- Si `product_uom_qty > 0` et (`state == 'cancel'` ou `quantity == 0`) -> `UserError` bloquant.

Plus permissif que `consumption=strict` : autorise les ecarts de pesee (poisson +/- 0,5 kg) tant qu'une consommation reelle est saisie.

### Hook 2 (par defaut OFF) - Conservation de masse
Si active dans Parametres > Fabrication :
- `sum(quantity sortie)` ne doit pas depasser `sum(quantity entree) * (1 + tolerance%)` apres conversion en kg.
- Tolerance par defaut : 5.0 %.

### Bypass
Champ booleen `skip_phantom_check` sur `mrp.bom` pour les recettes legitimes ou la sortie peut depasser l'entree (deconstructions speciales). Logge en `_logger.warning` quand utilise.

## Configuration

Parametres > Fabrication > section "SOPROMER - Anti stock fantome" :
- Toggle "Bloquer fabrications avec composant non consomme" (default ON)
- Toggle "Verifier conservation de masse" (default OFF)
- Champ "Tolerance masse (%)" (default 5.0)

## Installation

```bash
docker exec odoo-dev odoo -d SOPROMER -i sopromer_mrp_no_phantom --stop-after-init
```

## Compatibilite

- Odoo 18 Community + Enterprise
- Depends : `mrp` uniquement
