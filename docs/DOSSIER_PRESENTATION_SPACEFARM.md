# SpaceFarm 2080 — dossier complet pour le diaporama

État du code et de l'API vérifié le 24 septembre 2026. Projet étudiant EPSI Bachelor 3, workshop Horizon 2080, pilier 2 FoodTech & AgriTech.

## 1. Le projet en une minute

SpaceFarm est un prototype de mini-serre instrumentée pour imaginer la culture de plantes durant une mission spatiale longue. Une Arduino Yún lit les capteurs et transmet les valeurs au Raspberry Pi 3 par Wi-Fi. Le Pi les valide, les enregistre dans SQLite, sert l'interface web et décide de l'éclairage. Le tableau de bord rassemble les mesures, l'historique, l'état du système, les commandes et un scénario pédagogique de pénurie d'eau.

**Phrase orale :** « Notre prototype démontre la chaîne complète, du capteur à la décision automatique et à son retour dans l'interface. Nous séparons clairement les mesures physiques de la simulation de mission. »

## 2. Problème, objectifs et périmètre

- En mission longue, la serre doit être surveillée sans présence permanente d'un opérateur.
- L'eau, la lumière et la température sont des ressources à suivre. Une perte de réseau ou une mesure invalide doit être visible.
- Objectif MVP : température, humidité de l'air, luminosité relative, niveau d'eau estimé, distance à la plante, historique, état du Pi et LED automatique/manuelle.
- Objectif démonstration : simuler une réserve réduite à 40 % et répartir théoriquement l'eau entre plusieurs cultures.
- Le prototype actuel **ne fait pas pousser trois cultures avec une irrigation physique séparée**. Les profils de cultures, leurs besoins et Survival Mode sont des modèles de présentation.
- La pompe n'est pas branchée et n'est pas commandable en mode réel. L'interface affiche cette indisponibilité.

## 3. Architecture réellement utilisée

```text
DHT11 D2        ┐
Lumière A0      │
Eau A1          ├─> Arduino Yún ──HTTP/JSON sur Wi-Fi──> Raspberry Pi 3
HC-SR04 D7/D8   │          │                               │
LED D4          │          └──USB série 115200 vers PC     ├─> API Python / port 8000
Servo D9        ┘             (diagnostic, pas le flux     ├─> SQLite
                               du dashboard)               └─> React dans le navigateur

Navigateur ──GET /api/state toutes les 3 s──> Pi
Navigateur ──POST mode/lighting──────────────> Pi
Pi ──ordre dans réponse POST /api/ingest─────> Yún ──> LED D4
Yún ──état LED + accusé dans la mesure suivante───────────> Pi
```

Le Pi écoute sur `0.0.0.0:8000`. Adresse Wi-Fi vérifiée : **http://192.168.41.88:8000/?source=api**. L'adresse DHCP peut changer. Le 24 septembre, `raspberrypi.local` pointait vers `192.168.41.127`, où `/api/health` ne correspondait pas à SpaceFarm ; pour la présentation, vérifier l'URL avec `/api/health` plutôt que supposer que le nom mDNS désigne le bon service.

**Choix technique :** REST/HTTP et SQLite suffisent au workshop. Il n'y a ni broker MQTT ni second Pi nécessaires au fonctionnement constaté. La Yún initie toutes les connexions vers le Pi ; le Pi glisse un ordre éventuel dans sa réponse HTTP 201.

## 4. Matériel et branchements

| Matériel | Signal / broche Yún | Alimentation / précaution | Ce qui est vérifié |
| --- | --- | --- | --- |
| Arduino Yún | Micro-USB vers PC pour programmation ; Wi-Fi vers Pi | 5 V USB | Envoie les mesures au Pi |
| DHT11 nu, 4 broches | DATA → D2 | VCC 5 V, GND ; pull-up 10 kΩ entre VCC et DATA si absent | Température et humidité remontent |
| Module photorésistance 3 broches | S → A0 | + → 5 V, − → GND ; résistance sur le module | ADC remonte, sens inversé : plus sombre = ADC plus élevé |
| Water Level Detection Sensor | SIG → A1 | VCC 5 V, GND ; immerger uniquement les pistes | ADC remonte ; dernière lecture observée : 0 |
| HC-SR04 | TRIG → D7, ECHO → D8 | VCC 5 V, GND | Distance remonte dans l'API |
| LED témoin | D4 → résistance 220–330 Ω → anode ; cathode → GND | Ne jamais brancher sans résistance série | ON/OFF automatique testé physiquement |
| Servo SG90 | signal → D9 | Alimentation 5 V adaptée, masse commune | Code et télémétrie ; mouvement mécanique à confirmer sur le montage final |
| Ventilateur via L293D | ENABLE PWM → D11 | Moteur sur L293D, alimentation adaptée, masse commune ; jamais directement sur une broche | Code et valeur PWM ; moteur physique à confirmer |
| Raspberry Pi 3 Model B Rev 1.2 | Wi-Fi du lycée | Service Python et stockage sur carte microSD | API et interface répondent |

**D10 n'est pas utilisé** : `Servo.h` mobilise Timer1 sur la Yún, donc le PWM fiable du ventilateur est prévu sur D11. Il ne faut pas présenter D10 comme broche réellement câblée. Débrancher l'USB avant de modifier le circuit. Éviter d'alimenter le SG90 ou le moteur depuis une broche de sortie Arduino ; partager les masses si alimentation séparée. Aucune pompe ni sonde pH n'appartient au montage réel validé.

## 5. Ce que fait le programme Arduino

Fichier complet : `arduino/SpaceFarm_Yun_WiFi/SpaceFarm_Yun_WiFi.ino`.

1. `setup()` prépare les broches, DHT11, servo, port série à 115200 et Bridge de la Yún.
2. `loop()` déclenche un relevé environ toutes les 2 secondes avec `millis()` ; elle continue à lire la réponse HTTP pendant l'attente.
3. `readDHT()` lit température et humidité. Une mesure invalide devient `null` en JSON.
4. `readAnalogAverage()` lit A0 et A1 huit fois et moyenne, après avoir écarté la première conversion.
5. `readUltrasonic()` lance trois impulsions, limite chaque attente à 25 ms et utilise des échos cohérents ou une médiane. Une absence de mesure devient `null`.
6. `SENSOR_HEIGHT_CM = 30.0` est une **valeur à mesurer sur la serre**. `hauteur_plante = SENSOR_HEIGHT_CM − distance_plante` n'est une hauteur crédible que si le capteur vise correctement le sommet de la plante et la référence est mesurée.
7. `controlVentilation()` vise 0° sous 26 °C, 45° de 26 à moins de 28 °C et 90° à partir de 28 °C. Le ventilateur vaut 0 sous 28 °C, PWM 150 de 28 à 30 °C, 255 au-dessus de 30 °C. Une température DHT invalide arrête le ventilateur. La trappe conserve sa dernière position. Cette logique réside **dans la Yún**, pas dans le Pi.
8. `sendData()` écrit une ligne JSON sur l'USB et lance `curl` sur la partie Linux de la Yún vers `http://192.168.41.88:8000/api/ingest`. Les mesures envoyées sont notamment `temperature`, `humidity`, `light_raw`, `water_raw`, `distance_plante`, `hauteur_plante`, `servo`, `ventilateur`, `lighting`.
9. `readCommand()` lit une éventuelle commande `lighting 1 ID`, `lighting 0 ID` ou `servo ANGLE ID` dans la réponse du Pi. La LED D4 change d'état et l'identifiant est renvoyé comme `ack` dans l'envoi suivant. Le servo reprend sa régulation automatique après 30 s suivant une commande manuelle.

**Important pour la présentation :** le JSON USB a des clés françaises (`humidite`, `luminosite`, `niveau_eau`) ; le JSON Wi-Fi destiné à l'API a des clés adaptées au backend (`humidity`, `light_raw`, `water_raw`). Les deux sorties viennent du même relevé, mais le dashboard lit la base du Pi, pas le moniteur série du PC.

Exemple simplifié d'envoi Wi-Fi :

```json
{"sensor":"spacefarm-yun","ack":0,"readings":{"temperature":23.9,"humidity":58,"light_raw":{"value":481,"unit":"ADC"},"water_raw":{"value":0,"unit":"ADC"},"distance_plante":{"value":9,"unit":"cm"},"hauteur_plante":{"value":21,"unit":"cm"},"servo":0,"ventilateur":0,"lighting":0}}
```

Les nombres de l'exemple illustrent les valeurs observées le 24 septembre 2026 ; ce ne sont pas des constantes du programme.

## 6. Le code du Raspberry Pi, fichier par fichier

Tous les fichiers complets sont fournis dans `backend/` et dans l'archive `SpaceFarm_code_complet.zip` à la racine du projet. **Ne copier aucune base SQLite réelle ou identifiant dans le diaporama.**

| Fichier | Rôle exact |
| --- | --- |
| `server.py` | Lit la configuration, initialise SQLite, lance la purge et le serveur HTTP multithread |
| `routes.py` | Routes GET/POST, réception JSON, réponse à la Yún, construction du snapshot du dashboard, fichiers statiques |
| `db.py` | Validation, schéma SQLite, insertion, dernières valeurs, historique, alertes et purge |
| `calibration.py` | Conversion des ADC lumière/eau en pourcentages relatifs |
| `automation.py` | Mode automatique/manuel, seuils LED et consigne persistée |
| `commands.py` | File d'ordres avec délai d'expiration et accusés de réception |
| `system_info.py` | Modèle, OS, température CPU, mémoire, uptime du Pi |
| `ai_proxy.py` | Relais optionnel de l'assistant vers un service local du PC |
| `spacefarm.service` | Démarrage automatique du backend avec systemd |
| `test_*.py` | Tests backend et de calibration |

### Parcours précis d'une mesure dans `routes.py`

```text
POST /api/ingest
  → Handler._read_json()
  → Handler._authorised() (jeton optionnel ; configuration actuelle vide)
  → db.parse_payload() (format et valeurs)
  → db.store_readings() (SQLite + alertes)
  → commands.confirm() (accusé du dernier ordre)
  → automation.reconcile() (décision LED)
  → commands.take() (un ordre éventuel)
  → HTTP 201 {"command":"lighting 1 42", ...}
```

Le navigateur fait `GET /api/state`. La fonction `snapshot()` de `routes.py` relit les dernières mesures et l'historique dans SQLite, applique les conversions de `calibration.py`, ajoute les informations du Pi et renvoie un objet validé par le frontend avec Zod.

### Base de données

- Emplacement sur le Pi : `/var/lib/spacefarm/spacefarm.db`.
- `sensors` : registre des cartes connues et date du dernier envoi.
- `readings` : une ligne par mesure, avec capteur, métrique, valeur, unité, qualité et horodatage.
- `events` : journal des franchissements de seuil et des commandes confirmées.
- `commands` : ordres en attente, livrés et confirmés.
- `meta` : version de schéma, mode d'éclairage et consigne manuelle.
- Durée de conservation par défaut des relevés : 7 jours ; les événements sont limités à 500. Le but est de limiter la croissance de la base sur carte microSD.

### Service et API

Le fichier `backend/spacefarm.service` lance `/usr/bin/python3 -B /home/pi/spacefarm/backend/server.py --host 0.0.0.0 --port 8000` sous l'utilisateur `pi`. Le frontend compilé est servi depuis `/home/pi/spacefarm/frontend/dist`. Le code backend est Python standard (`http.server`, `sqlite3`) sans framework web ni broker MQTT.

| Route | Fonction |
| --- | --- |
| `GET /api/health` | Identifier le service SpaceFarm |
| `GET /api/state` | Vue complète affichée sur la page |
| `GET /api/metrics` | Mesures récentes, dont valeurs brutes ADC |
| `GET /api/history` | Série temporelle ; filtres heures/points/métrique |
| `GET /api/sensors` | Cartes connues, vues en ligne ou hors ligne |
| `GET /api/stats` | Nombre de mesures, capteurs et métriques |
| `POST /api/ingest` | Réception des relevés Yún et retour éventuel d'un ordre |
| `POST /api/mode` | `{"mode":"automatic"}` ou `{"mode":"manual"}` |
| `POST /api/actuators` | En manuel : `{"actuator":"lighting","enabled":true}` ou `false` |

### Automatisation de la LED

Sur ce module A0, **plus l'ADC est élevé, plus il fait sombre**. En mode automatique, le Pi allume la LED si `light_raw ≥ 650`, l'éteint si `light_raw ≤ 450` et garde l'état précédent entre les deux. Les deux seuils évitent une oscillation rapide au voisinage d'un seul seuil. Le mode manuel conserve l'état présent lors du changement de mode, puis le bouton Éclairage fixe ON/OFF. Le Pi transmet la commande dans la réponse au prochain relevé de la Yún ; l'état de la LED remonte ensuite comme `lighting`.

La pompe est explicitement refusée par `/api/actuators`. La présence de noms de commandes historiques dans `commands.py` ne signifie pas qu'une pompe est câblée ou pilotée par le dashboard actuel.

## 7. Calibration, mesures et unités

| Grandeur | Source | Calcul affiché | Limite |
| --- | --- | --- | --- |
| Température de l'air | DHT11 | °C envoyés par le capteur | Résolution et précision modestes du DHT11 |
| Humidité de l'air | DHT11 | % envoyé par le capteur | Ce n'est pas l'humidité du sol |
| Luminosité | A0 brut, 0–1023 ADC | `100 × (ADC − 1015) / (220 − 1015)`, borné à 0–100 % | **Indice relatif**, pas des lux ; repères provisoires |
| Niveau d'eau | A1 brut, 0–1023 ADC | `100 × ADC / 717`, borné à 0–100 % | Estimation dépendante de l'immersion et du réservoir |
| Volume d'eau | Niveau estimé + capacité configurée | `0,05 L × niveau / 100` | 50 mL est une hypothèse de configuration, pas un débit mesuré |
| Distance | HC-SR04 | Durée de l'écho × vitesse du son / 2 | Mauvais écho possible selon l'orientation et les feuilles |
| Hauteur de plante | Distance + `SENSOR_HEIGHT_CM` | `30 cm − distance` dans le code actuel | 30 cm doit être mesuré sur le montage final |
| Température CPU du Pi | `/sys` | °C système | À ne jamais confondre avec la température de la serre |

Le 24 septembre 2026 vers 10 h 14 à Paris, l'API montrait environ **23,9 °C, 58 % d'humidité, 481 ADC sur A0, 0 ADC sur A1, 9 cm de distance, 21 cm de hauteur calculée, LED OFF**. Le réservoir affichait 0 % parce que la sonde rapportait 0 ADC à cet instant ; cela **ne prouve pas à lui seul qu'un réservoir entier est vide**. La valeur de hauteur ne prouve pas une croissance réelle : elle résulte de la référence de 30 cm. Les valeurs de capteur et l'état du Pi évoluent continuellement ; les captures doivent être datées.

## 8. Dashboard : ce que voit le jury

Le frontend est écrit en **React 19 + TypeScript**, construit avec **Vite**. **Recharts** dessine les courbes, **Zod** valide les réponses API, **Lucide** fournit les icônes. Le thème est sombre, lisible et responsive. Le navigateur interroge `/api/state` toutes les 3 secondes et désactive les commandes si l'API est perdue ou si l'état matériel devient indisponible.

| Zone | Présentation et statut |
| --- | --- |
| En-tête / état global | Source Raspberry Pi ou démonstration ; NORMAL, ATTENTION ou CRITIQUE calculé à partir des valeurs et de la connexion |
| Quatre cartes | Température, humidité de l'air, luminosité relative, niveau du réservoir ; mesure absente clairement indiquée |
| Historique | Courbes sur 1, 6 ou 24 h ; min/moyenne/max ; vrai historique SQLite en mode Pi, synthétique en mode démo |
| Automatisation | Automatique/manuel ; LED physique commandable ; pompe non branchée et grisée en mode Pi |
| Cultures | Laitue romaine, basilic, tomate ; priorités et allocations **théoriques** |
| Croissance et aération | Distance, hauteur estimée, angle de servo, valeur PWM du ventilateur remontés par la Yún |
| État du système | API connectée, capteurs disponibles, dernière réponse, CPU, uptime et mémoire du Pi |
| Eau | Volume estimé sur la base de 50 mL ; autonomie réelle masquée tant que le débit n'est pas mesuré |
| Journal | Alertes de seuil, présence des capteurs et accusés d'ordres ; filtre des alertes |
| Survival Mode | Lien vers une simulation isolée : budget d'eau réduit à 40 %, priorité laitue, basilic réduit, tomate suspendue |
| Assistant | Interface facultative d'analyse des mesures avec ChatGPT/Codex via un relais sur le PC ; ne pilote aucun actionneur et exige PC, tunnel et connexion actifs |

Le bandeau actuel de la page peut encore afficher une phrase générique disant que les capteurs ne sont pas configurés. C'est un **texte resté ancien dans `frontend/src/App.tsx`**, alors que les mesures réelles apparaissent. Ne pas reprendre cette phrase dans le diaporama comme une preuve d'absence de capteurs.

## 9. Démonstration et séparation du réel

- URL réelle : `?source=api` ; les tuiles lisent le Pi.
- URL de démo : `?source=mock` ; les valeurs sont produites par `frontend/src/data/engine.ts` dans le navigateur, sans agir sur le matériel.
- Le scénario « seulement 40 % d'eau » appartient **uniquement à la démo** ; le bouton en vue réelle ouvre la démo.
- Dans la démo, la pompe effectue des cycles logiciels fictifs ; aucune pompe physique ne tourne. Les besoins des trois cultures ne sont pas mesurés.
- Les profils fictifs sont : laitue romaine principale 1,2 L/j (1,05 L/j en crise), basilic secondaire 0,72 L/j (0,45 en crise), tomate expérimentale 0,48 L/j (0 en crise). Ces litres servent au scénario pédagogique et **ne correspondent pas** au petit réservoir physique de 50 mL.
- Aucun calcul sérieux d'autonomie réelle n'est possible sans mesurer le débit de pompe et la consommation effective ; la vue réelle affiche donc « débit à mesurer ».

## 10. Historique du développement et changements

1. Prototype de tableau de bord d'abord utilisable en mode simulation, avec quatre mesures, courbes, journal et scénario de crise.
2. Installation de l'interface et de l'API Python sur Raspberry Pi 3 ; lecture de l'état système réel.
3. Raccordement de l'Arduino Yún par Wi-Fi ; DHT11, lumière et eau envoyés avec `POST /api/ingest`, confirmation HTTP 201.
4. Ajout de SQLite pour conserver et relire les mesures et l'historique.
5. Remplacement des « lux » apparents par une **luminosité relative en %**, car le module photorésistance n'a pas été étalonné avec un luxmètre.
6. Calibration provisoire du niveau d'eau, basée sur une sonde sèche et une immersion partielle ; capacité de présentation ramenée à 50 mL.
7. Ajout du capteur ultrason, de la hauteur estimée et du code de trappe/ventilateur sur la Yún.
8. Ajout de la LED D4 : d'abord test de câblage, puis décision automatique déplacée sur le Pi avec mode manuel sur le site ; aller-retour des ordres et accusés testé.
9. Ajout facultatif d'un panneau assistant qui analyse les mesures via un relais sur le PC ; **il ne décide pas de l'arrosage et ne commande pas la LED**.

## 11. Ce qui est confirmé, ce qui reste à confirmer

**Confirmé par le code, les tests et l'API :** dashboard en ligne, Yún en ligne, DHT11, A0, A1, HC-SR04, stockage SQLite, historique, état du Pi, retour d'état LED, mode automatique/manuel, LED physiquement allumée/éteinte lors des tests du 23 septembre. Le 24 septembre, `/api/health` a répondu `spacefarm`, et `/api/state` contenait des relevés frais.

**Dans le code mais à valider physiquement pour le jury :** déplacement réel de la trappe avec SG90, moteur de ventilateur avec L293D et alimentation externe, orientation fixe du HC-SR04, mesure exacte de `SENSOR_HEIGHT_CM`, fixation verticale de la sonde d'eau et calibration dans le vrai réservoir.

**Simulation ou option :** trois cultures et allocation d'eau, Survival Mode, cycles de pompe en mode démo, assistant ChatGPT qui dépend du PC.

**Absent du prototype réel :** pompe d'irrigation, mesure de débit, mesure de pH, mesure réelle en lux, décision d'arrosage par IA, système totalement autonome en cas de panne de réseau.

**Risques/limites à annoncer honnêtement :** le code Yún et l'URL de présentation contiennent l'IP Wi-Fi `192.168.41.88`, qui peut changer ; réseau HTTP local sans authentification du bouton LED ; étalonnages eau/lumière provisoires ; une valeur `servo: 0` ou `ventilateur: 0` dans l'API est une consigne logicielle, pas une preuve de mouvement physique ; la LED garde son dernier état si le Pi ne répond plus.

## 12. Tests et preuves à montrer

- `GET http://192.168.41.88:8000/api/health` → `status: ok`, service `spacefarm`, version `0.3.0`.
- `GET /api/state` → mesures récentes, `mode: automatic`, LED et statut matériel.
- `GET /api/metrics` → `light_raw` et `water_raw` en ADC, montrant que l'affichage est calculé à partir de valeurs reçues.
- `GET /api/sensors` → carte `spacefarm-yun` en ligne lors de la vérification du 24 septembre.
- Test physique du 23 septembre : couvrir la photorésistance → valeur ADC élevée → ordre d'allumage → LED ON ; découvrir → ADC basse → LED OFF.
- Test manuel du 23 septembre : mode manuel, LED ON puis OFF depuis le dashboard ; accusés reçus, retour au mode automatique.
- Tests automatisés validés après l'implémentation : 31 tests backend ; tests frontend et compilation Vite passés.
- Captures à préparer : vue d'ensemble réelle, courbe historique, panneau automatisation, montage global, gros plan des broches, test LED, vue Survival Mode **avec étiquette Simulation**.

Commandes de vérification non destructives :

```powershell
Invoke-RestMethod http://192.168.41.88:8000/api/health
Invoke-RestMethod http://192.168.41.88:8000/api/state
Invoke-RestMethod http://192.168.41.88:8000/api/metrics
```

Sur le Pi, si l'accès SSH est disponible :

```sh
systemctl status spacefarm.service
journalctl -u spacefarm.service -n 50 --no-pager
ls -lh /var/lib/spacefarm/spacefarm.db
```

Pour compiler et tester localement depuis la racine du projet :

```powershell
python -B -m unittest discover -s backend -v
cd frontend
npm.cmd install
npm.cmd test
npm.cmd run build
```

Dans Arduino IDE, ouvrir `arduino/SpaceFarm_Yun_WiFi/SpaceFarm_Yun_WiFi.ino`, sélectionner **Arduino Yún** et son port COM, installer **DHT sensor library** et **Adafruit Unified Sensor** ; `Bridge`, `Process` et `Servo` sont nécessaires au sketch. Compiler, téléverser, puis ouvrir le moniteur série à **115200 bauds**.

## 13. Plan de diaporama conseillé (18 diapositives)

| N° | Titre | À afficher | À dire en 1 phrase |
| --- | --- | --- | --- |
| 1 | SpaceFarm 2080 | Nom, équipe, EPSI, photo du prototype | « Une mini-serre instrumentée pensée pour les contraintes d'une mission spatiale. » |
| 2 | Problématique | Eau, lumière, surveillance, mission longue | « Sans suivi ni automatisation, une panne ou pénurie peut compromettre la culture. » |
| 3 | Objectifs | Mesurer, enregistrer, visualiser, agir, simuler | « Nous avons visé une chaîne fonctionnelle et une démonstration de gestion de crise. » |
| 4 | Architecture | Schéma Yún → Wi-Fi → Pi/API/SQLite → dashboard | « La Yún mesure, le Pi stocke et décide, le navigateur affiche. » |
| 5 | Matériel | Photo annotée Yún, Pi, capteurs, LED | « Chaque capteur a une broche et une fonction identifiées. » |
| 6 | Câblage | Tableau des broches ; alimentation séparée moteur/servo | « Le moteur ne se branche jamais directement sur une sortie de la Yún. » |
| 7 | Acquisition | Extrait du JSON envoyé toutes les ~2 s | « Les données brutes sont transmises au Pi avant conversion pour l'affichage. » |
| 8 | API et stockage | Étapes `ingest → validation → SQLite → state` | « Chaque lecture est vérifiée puis historisée. » |
| 9 | Centre de contrôle | Capture réelle datée | « Une seule page montre les quatre mesures prioritaires et l'état global. » |
| 10 | Historique et alertes | Courbe + journal | « Nous suivons les évolutions, pas seulement la valeur du moment. » |
| 11 | Lumière | Valeur ADC, calcul relatif, seuils 650/450 | « La valeur brute monte quand il fait sombre ; le Pi allume alors la LED. » |
| 12 | Automatisation | Test couvert/découvert, manuel ON/OFF | « La décision et le retour d'état ont été vérifiés sur le montage. » |
| 13 | Eau | Sonde, réservoir 50 mL, limites calibration | « Le niveau est estimé ; il ne mesure pas un volume absolu sans étalonnage. » |
| 14 | Croissance et aération | HC-SR04, formule de hauteur, trappe/ventilation | « La distance fournit une hauteur estimée ; les actionneurs restent à valider mécaniquement. » |
| 15 | Survival Mode | Capture **Simulation** : 40 %, priorités | « Ce scénario explique une stratégie de réduction, sans agir sur le matériel. » |
| 16 | Évolutions du prototype | Timeline des changements | « Nous avons corrigé l'unité de lumière, ajouté l'historique et relié les commandes au Pi. » |
| 17 | Résultats et limites | Réel / simulé / absent ; tests | « Nous présentons les résultats prouvés et les limites du prototype. » |
| 18 | Suite du projet | Fixation, calibration, pompe + sécurité, IP stable | « La V2 porterait sur l'irrigation réelle et un étalonnage reproductible. » |

Prévoir une courte démonstration live après la diapositive 12 ; avoir des captures enregistrées si le Wi-Fi du lycée tombe. Afficher systématiquement **RÉEL** ou **SIMULATION** sur les diapositives de résultats.

## 14. Questions possibles du jury

**Pourquoi pas MQTT ?** Pour un seul capteur principal et un seul Pi, HTTP/JSON est plus simple à installer et à déboguer. MQTT serait intéressant si les cartes et messages se multipliaient.

**Pourquoi deux cartes ?** La Yún lit et pilote les broches ; le Pi héberge l'API, SQLite et le site. Le navigateur ne lit jamais directement les capteurs.

**Pourquoi le navigateur n'automatise pas la LED ?** La décision réside sur le Pi et continue si la page est fermée. La Yún applique l'ordre reçu et renvoie son état.

**Est-ce que 66 % de lumière équivaut à 660 lux ?** Non. Le % est un indice relatif entre deux valeurs ADC observées. Il faudrait un luxmètre de référence, plusieurs points d'étalonnage et une géométrie d'éclairage stable pour annoncer des lux approximatifs.

**Le réservoir affiche-t-il exactement 50 mL ?** Non. 50 mL est la capacité configurée ; la sonde estime un pourcentage selon sa profondeur d'immersion. Une calibration à sec et à plusieurs volumes connus dans un réservoir fixe est nécessaire.

**Comment l'IA pilote-t-elle la pompe ?** Elle ne la pilote pas. L'assistant facultatif fournit uniquement une analyse textuelle des mesures ; aucune pompe réelle n'est câblée.

**Qu'arrive-t-il en panne Wi-Fi ?** Le site marque les données périmées et désactive les commandes. La Yún peut continuer à lire ses capteurs et réguler localement servo/ventilateur ; la LED conserve son dernier état tant qu'aucun nouvel ordre ne vient du Pi.

**Pourquoi un capteur ultrason pour la croissance ?** C'est une démonstration sans contact de la distance au sommet de la plante. Le montage doit être fixe et la hauteur de référence mesurée ; les feuilles et le pot peuvent perturber l'écho.

**Votre prototype est-il autonome pour une vraie mission spatiale ?** Non. C'est un prototype pédagogique terrestre. Il manque notamment fiabilité à long terme, redondance, contrôle d'irrigation physique, alimentation sécurisée, étalonnage et validation agronomique.

## 15. Code à projeter pendant la présentation

Privilégier quatre courts extraits : `arduino/...ino` pour `sendData()` ; `backend/routes.py` pour `POST /api/ingest` ; `backend/db.py` pour `store_readings()` ; `backend/automation.py` pour les seuils LED. Afficher le fichier entier uniquement si le jury le demande : les liens et l'archive de code fournis avec ce dossier contiennent l'ensemble. Le frontend commence dans `frontend/src/App.tsx` et le chemin réel/mock est dans `frontend/src/data/provider.ts`.
