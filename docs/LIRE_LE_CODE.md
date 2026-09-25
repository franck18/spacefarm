# Lire le code SpaceFarm

## Le trajet d'une mesure

Yún → `POST /api/ingest` → validation → SQLite → `GET /api/state` → React.

## Backend : commencer ici

1. `backend/server.py` lance le serveur et ouvre la base.
2. Dans `backend/routes.py`, `do_POST()` choisit l'action demandée.
3. `_receive_measurements()` reçoit les mesures de la Yún.
4. `db.parse_payload()` vérifie le JSON ; `db.store_readings()` l'enregistre.
5. `automation.reconcile()` décide de l'état de la LED.
6. `commands.py` transmet l'ordre et reçoit sa confirmation.
7. `snapshot()` prépare les données affichées sur le site.

`calibration.py` convertit les ADC en %. `system_info.py` lit l'état du Pi.
`ai_proxy.py` transmet les demandes à l'assistant du PC.

Les mesures sont stockées sur le Pi dans `/var/lib/spacefarm/spacefarm.db`.
Les références de calibration, seuils et routes HTTP sont conservés.

## Frontend : commencer ici

1. `frontend/src/main.tsx` ouvre React.
2. `App.tsx` assemble les panneaux et choisit le message d'état global.
3. `hooks/useSpaceFarm.ts` actualise les données toutes les 3 secondes.
4. `data/provider.ts` choisit l'API du Pi ou la démonstration locale.
5. `data/types.ts` vérifie les réponses et définit les unités affichées.
6. `components/` contient un fichier par panneau.

`data/engine.ts` contient uniquement les calculs de simulation.
`styles.css` contient la présentation visuelle.
La simulation conserve son moteur existant ; la pompe est masquée dans l'interface.

## Pourquoi garder les validations ?

Une mesure absente ne doit pas devenir zéro. Une ancienne valeur en lux ne doit
pas être affichée comme un pourcentage. Une commande doit rester bloquée lorsque
la carte ne répond plus. Ces vérifications font partie du fonctionnement utile.

## Nettoyage effectué

- Routes POST séparées en fonctions courtes.
- Dernières mesures lues en un seul appel dans `snapshot()`.
- Conversion ADC commune pour l'eau et la lumière.
- Conditions imbriquées remplacées par des variables nommées.
- JSX et CSS présentés sur plusieurs lignes lisibles.
- Commentaires courts en français sur les rôles et les règles importantes.
- Ancien composant `CultivationPanel.tsx` retiré car il n'était plus affiché.

Les sauvegardes avant nettoyage sont dans `backups/simplification-20260924`
sur le PC et `/home/pi/spacefarm/backups/simplification-20260924` sur le Pi.
