# Lire le backend SpaceFarm

Commencer par `server.py`, puis `routes.py`, puis `db.py`.

| Fichier | Rôle |
| --- | --- |
| `server.py` | Lit les options et démarre le serveur. |
| `routes.py` | Reçoit les mesures et répond au navigateur. |
| `system_info.py` | Lit température CPU, mémoire et disponibilité du Pi. |
| `db.py` | Vérifie, enregistre, relit et purge les mesures. |
| `calibration.py` | Convertit les valeurs analogiques en indices relatifs. |
| `automation.py` | Décide sur le Pi de l'état de la LED. |
| `commands.py` | Met les ordres en attente et lit les accusés de réception. |
| `test_server.py` | Vérifie le fonctionnement avec des bases temporaires. |

## Une mesure arrive

1. La Yún envoie un JSON sur `POST /api/ingest`.
2. `routes.Handler.do_POST()` lit ce JSON avec `_read_json()`.
3. `db.parse_payload()` vérifie son contenu.
4. `db.store_readings()` ajoute les mesures dans SQLite.
5. `automation.reconcile()` compare la luminosité et l'état de la LED.
6. La réponse HTTP 201 confirme l'enregistrement et contient, si nécessaire, un ordre pour la Yún.

## Le navigateur affiche les données

`GET /api/state` appelle `routes.snapshot()`, qui lit la base et les
informations du Raspberry. Les autres routes fournissent l'historique,
les cartes connectées, les métriques et les fichiers de l'interface.

Sur le Pi, la base est `/var/lib/spacefarm/spacefarm.db`.
Le service existant lance toujours `/home/pi/spacefarm/backend/server.py`.

## Luminosité relative

`calibration.py` convertit `light_raw` en un indice borné entre 0 et 100 %.
Références provisoires : 1015 ADC dans l'obscurité et 220 ADC éclairé. Sur ce module, la valeur brute augmente quand la lumière baisse.
La tuile et l'historique de `/api/state` utilisent cette même conversion.
Les données brutes restent intactes dans SQLite et `/api/metrics`.
Ce n'est ni une mesure en lux, ni un pourcentage physique de lumière.
Revérifier les références après rebranchement ou changement d'éclairage.

## Éclairage réel

En mode automatique, une valeur `light_raw` d'au moins 650 ADC allume la LED ; 450 ADC ou moins l'éteint. Entre ces seuils, elle conserve son état pour éviter les clignotements. En mode manuel, le tableau de bord envoie une consigne ON/OFF au Pi. Le mode et la consigne sont conservés dans SQLite. La pompe n'est pas commandable.

Depuis la racine du projet, lancer les tests avec :

```sh
python3 -B -m unittest discover -s backend -v
```
