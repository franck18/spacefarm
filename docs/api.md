# Raspberry Pi et API SpaceFarm

## Accès et fonctionnement

Sur le réseau Wi-Fi du lycée, ouvrir http://192.168.41.88:8000/ (adresse DHCP susceptible de changer). L'application est installée dans `/home/pi/spacefarm` et lancée par `spacefarm.service`. Le Pi sert l'interface et l'API sur le port 8000. Sa base SQLite est `/var/lib/spacefarm/spacefarm.db` ; elle conserve les mesures, le mode d'éclairage et les commandes.

L'Arduino Yún transmet ses mesures au Pi par Wi-Fi environ toutes les deux secondes avec `POST /api/ingest`. La réponse HTTP 201 peut contenir un ordre compact pour la Yún ; celle-ci renvoie un accusé de réception avec la mesure suivante. Le Pi fournit aussi sa température CPU, sa mémoire et sa durée de fonctionnement. La température CPU ne représente pas celle de la culture.

## Matériel raccordé

| Élément | Broche Yún | Utilisation |
| --- | --- | --- |
| DHT11 | D2 | Température et humidité de l'air |
| Module photorésistance | A0 | `light_raw` en ADC |
| Sonde de niveau d'eau | A1 | `water_raw` en ADC |
| HC-SR04 | D7 TRIG, D8 ECHO | Distance et hauteur estimée de la plante |
| Servo SG90 | D9 | Trappe d'aération |
| LED | D4 | Éclairage commandé par le Pi |

La pompe et le ventilateur ne sont pas commandables depuis le tableau de bord actuel. Le mode démonstration (`?source=mock`) reste indépendant du matériel ; la vue réelle utilise `?source=api`. Une erreur de l'API ne déclenche pas de fausses mesures simulées.

## Routes utiles

| Méthode et route | Rôle |
| --- | --- |
| `GET /api/health` | Vérifier que le serveur répond |
| `GET /api/state` | État complet du tableau de bord, dont mode et LED |
| `GET /api/metrics` | Dernières mesures, y compris valeurs ADC brutes |
| `GET /api/history` | Historique des mesures |
| `GET /api/sensors` | État des capteurs |
| `GET /api/stats` | Statistiques |
| `POST /api/ingest` | Réception des mesures de la Yún |
| `POST /api/mode` | `{"mode":"automatic"}` ou `{"mode":"manual"}` |
| `POST /api/actuators` | En mode manuel uniquement : `{"actuator":"lighting","enabled":true}` (ou `false`) |

Le tableau de bord désactive les commandes si la télémétrie de la LED Yún est absente ou périmée. Les commandes de pompe sont refusées. Les commandes du tableau de bord ne disposent actuellement pas d'une authentification utilisateur : tout appareil capable de joindre ce Pi sur le réseau local peut commander la LED. Ne pas exposer le port 8000 à Internet sans ajouter un contrôle d'accès.

## Calibration et automatisation

Le module de photorésistance produit une valeur ADC **élevée dans le noir**. `backend/calibration.py` affiche une luminosité relative de 0 à 100 %, avec les repères provisoires 1015 ADC (couvert) et 220 ADC (éclairé). Ce pourcentage n'est pas une mesure en lux. Le niveau d'eau est également un pourcentage estimé à partir de 0 ADC à sec et 717 ADC pour une immersion de référence ; la capacité configurée du réservoir est 50 mL. La sonde tenue à la main et la forme du réservoir limitent la précision de ce pourcentage.

En mode automatique, `backend/automation.py` allume la LED à partir de 650 ADC et l'éteint à 450 ADC ou moins. Entre les deux seuils, elle garde son état pour éviter le clignotement. En mode manuel, les boutons du site donnent la consigne au Pi ; le Pi la transmet à la Yún et reçoit ensuite son état réel. L'automatisation tourne sur le Pi même si le navigateur est fermé.

## Exploitation et tests

Sur le Pi :

```sh
systemctl status spacefarm.service
journalctl -u spacefarm.service -n 50 --no-pager
sudo systemctl restart spacefarm.service
```

Depuis la racine du projet sur le PC, exécuter `python3 -B -m unittest discover -s backend -v` pour le backend, puis `npm.cmd test` et `npm.cmd run build` dans `frontend`. Le serveur Python utilise la bibliothèque standard et SQLite ; le schéma des réponses du tableau de bord se trouve dans `frontend/src/data/types.ts`.
