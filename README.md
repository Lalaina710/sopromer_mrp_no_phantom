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

## Test fonctionnel (validé sur 45)

Cas test : BoM 21 (FILETAGE 3DENTS GM) requiert composant TRTDE05.
- Stock TRTDE05 disponible : 0.30 kg
- MO créée avec qty 10 kg → qty composant requise = 10 kg
- Clic Confirmer → popup "Opération invalide" :

```
Stock matière insuffisant — confirmation MO impossible.
Composant : [TRTDE05] Trois dents extra
Qty requise : 10.000 kg
Stock disponible @ US/Depot US : 0.000 kg
Manque : 10.000 kg
Action : effectuer la réception ou l'inventaire de la matière première avant de confirmer cette fabrication.
```

## Combo modules anti-fantôme

Le module fait partie d'un combo SOPROMER recommandé :
- `stock_no_negative` (OCA Akretion) — bloque stock physique négatif via constraint stock.quant
- `sopromer_mrp_no_phantom` — bloque MO confirm si stock matière insuffisant + qty=0 silencieux (ce module)
- `sopromer_lot_delivery_wizard` v1.7.1+ — wizard FIFO multi-lots BL ventes

Couvre 95% des cas fantôme/négatif/traçabilité sans bascule globale BoM strict (qui bloquerait pesée variable poisson).

## Déploiement

| Environnement | Serveur | DB cible | Statut |
|---------------|---------|----------|--------|
| TEST | `192.73.0.45` | `SOPROMER-REST2904` | ✅ installé v18.0.1.1.0 |
| PROD | `192.73.0.43` | `SOPROMER` | ✅ installé v18.0.1.1.0 (2026-04-30) |

## Historique de versions

- **v18.0.1.1.0** (2026-04-30) — Initial release : block phantom stock at MO confirm + qty=0 hook + mass balance toggle.
