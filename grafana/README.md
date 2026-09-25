# Grafana SpaceFarm

Adresse : http://192.168.41.88:3000/d/spacefarm-2080

Le centre de contrôle reste sur le port 8000 pour commander la LED.
Grafana lit `/api/state` avec le plugin Infinity. Aucun accès direct à SQLite,
aucune nouvelle base de mesures et aucune modification du sketch Arduino.

## Affichage

- Température, humidité, luminosité relative et niveau d'eau estimé.
- Luminosité et eau en **%**, avec les conversions du backend existant.
- Quatre courbes sur les **six dernières heures** fournies par l'API.
  Choisir une période plus ancienne dans Grafana ne charge pas d'archives supplémentaires.
- État confirmé de la LED, mode, température CPU et mémoire du Pi.
- Rafraîchissement toutes les 30 secondes.
- Une valeur invalide ou périmée est « Indisponible », jamais remplacée par zéro.

Le pourcentage d'eau reste une estimation de la sonde : le changement
d'alimentation vers D3 et la position du capteur nécessitent de vérifier
la calibration. Grafana ne corrige pas la précision physique du capteur.

## Accès

Connexion obligatoire avec le compte `admin`. Le mot de passe aléatoire est dans
`C:\Users\yusuk\Downloads\SpaceFarm_Grafana_acces.txt` sur le PC.
Ce fichier est extérieur au projet : ne pas le diffuser dans les archives.
Sur le Pi, la configuration initiale utilise `/etc/grafana/spacefarm-admin-password`.
Un changement ultérieur du mot de passe dans Grafana doit être reporté dans le fichier du PC.

## Fichiers

- `generate_dashboard.py` : génération du dashboard, avec commentaires courts.
- `spacefarm.json` : dashboard généré.
- `datasource.yaml` : connexion HTTP à l'API locale, méthodes dangereuses désactivées.
- `provider.yaml` : chargement automatique du dashboard.
- `grafana.ini` : thème sombre, compte protégé, port 3000.
- `configure.sh` : déploiement de ces fichiers, conservation de la configuration initiale.

## Réinstallation sur le Raspberry Pi

Installer Grafana OSS depuis son dépôt APT officiel :
https://grafana.com/docs/grafana/latest/setup-grafana/installation/debian/

Versions installées le 24/09/2026 : Grafana 13.2.2 ARMv7, Infinity 4.0.0.

```sh
sudo /usr/share/grafana/bin/grafana cli --homepath /usr/share/grafana --pluginsDir /var/lib/grafana/plugins plugins install yesoreyeram-infinity-datasource
cd /home/pi/spacefarm/grafana
python3 generate_dashboard.py
sh configure.sh
```

Le script de configuration doit être lancé par un utilisateur ayant sudo.
Le mot de passe initial est généré uniquement si son fichier n'existe pas.
Le service démarre automatiquement avec le Pi.

```sh
systemctl status grafana-server
journalctl -u grafana-server -n 30 --no-pager
curl http://127.0.0.1:3000/api/health
```

Pour arrêter Grafana et libérer sa mémoire : `sudo systemctl stop grafana-server`.
Cela n'arrête ni SpaceFarm ni l'automatisation. Pour désactiver son démarrage :
`sudo systemctl disable grafana-server`.

Le dashboard est géré par les fichiers : modifier le générateur, le relancer,
puis recopier `spacefarm.json` vers `/var/lib/grafana/dashboards/spacefarm.json`.
Les graphiques ne modifient pas la base de mesures.

## Alertes e-mail

Destinataire et expéditeur : `yusuke59160@gmail.com`.
Envoi Gmail sur le port 587, avec STARTTLS obligatoire et certificat vérifié.
Le mot de passe d'application est uniquement dans le fichier protégé
`/etc/grafana/spacefarm-smtp-password` sur le Pi (root:grafana, 640),
jamais dans le code. Il est nécessaire avant de relancer `configure.sh`.

Règles évaluées chaque minute :

- Réservoir estimé sous 20 % pendant 5 minutes.
- Température sous 18 °C ou au-dessus de 30 °C pendant 5 minutes.
- Une mesure invalide ou périmée pendant 2 minutes. L'API considère une
  mesure périmée après 120 secondes sans actualisation.

Les erreurs de lecture de l'API déclenchent également un état d'alerte.
Les valeurs absentes ne sont pas traitées comme de l'eau à 0 % ni une température de 0 °C.
Après déclenchement, Grafana attend 30 secondes pour regrouper les notifications.
Un rappel est envoyé toutes les 4 heures si le problème persiste, et un message
est envoyé lors du retour à la normale.

Les seuils servent au prototype et ne constituent pas une recommandation agronomique.
L'alerte d'eau dépend de la calibration de la sonde.
Si le Pi est éteint ou sans Internet, il ne peut pas envoyer d'e-mail.

`generate_alerts.py` génère `alerts.json`, déployé dans
`/etc/grafana/provisioning/alerting/spacefarm.json`.
`alerts.pending.json` conserve la préparation initiale en pause et n'est pas déployé.
Les règles actives sont visibles dans le menu Alerting de Grafana.
