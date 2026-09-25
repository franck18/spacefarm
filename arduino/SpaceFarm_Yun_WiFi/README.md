# SpaceFarm 2080 — Arduino Yún

Le sketch `SpaceFarm_Yun_WiFi.ino` conserve l'envoi HTTP par le Wi-Fi de la Yún vers `http://192.168.41.88:8000/api/ingest`. Il transmet aussi une ligne JSON toutes les deux secondes sur le port USB série à **115200 bauds**. L'adresse du Pi peut changer ; modifier `API_URL` si nécessaire.

## Branchements

| Élément | Yún | Autres connexions |
| --- | --- | --- |
| DHT11 DATA | D2 | VCC 5 V, GND ; résistance 10 kΩ entre VCC et DATA si le module n'en possède pas |
| Module photorésistance, broche S | A0 | Broche + vers 5 V, broche − vers GND ; aucune résistance externe |
| Niveau d'eau SIG | A1 | VCC → D3 uniquement ; GND → GND |
| HC-SR04 TRIG / ECHO | D7 / D8 | VCC 5 V, GND |
| LED témoin, longue patte | **D4 via résistance 220 à 330 Ω** | Courte patte vers GND |
| SG90 signal | D9 | Alimentation 5 V adaptée, masse commune |
| L293D ENABLE du canal utilisé | **D11** | Entrées IN1/IN2 fixées matériellement pour un sens ; alimentations logique et moteur séparées selon le moteur ; masse commune |

**D10 reste libre.** Sur la Yún, `Servo.h` utilise Timer1 et empêche le PWM normal de D10 ; D11 fonctionne avec un autre minuteur. Avant de brancher le moteur, couper l'alimentation. Le moteur se branche aux sorties du L293D, jamais sur une broche de la Yún. Alimenter de préférence le SG90 et le moteur par une alimentation 5 V externe adaptée, avec le GND relié au GND de la Yún. Ne pas confondre alimentation logique du L293D et alimentation moteur.

## Mesures et commandes

Depuis le 24/09, D3 alimente uniquement la petite sonde d'eau pendant chaque mesure : HIGH, stabilisation de 10 ms avec `millis()`, moyenne de huit lectures A1, puis LOW. Débrancher l'USB avant de déplacer le VCC de la sonde du 5 V vers D3. Ne pas relier D3 au rail 5 V partagé. Le module doit consommer un courant compatible avec une sortie numérique ; utiliser un transistor si ce n'est pas le cas. Revérifier les références à sec et immergée : l'ancienne calibration sur alimentation 5 V permanente peut changer.

- `temperature` et `humidite` : DHT11, en °C et %. Une erreur produit `null`.
- `luminosite` et `niveau_eau` : valeurs brutes ADC 0–1023, sans conversion en lux ni en pourcentage.
- `distance_plante` : distance ultrason en cm. Trois échos sont lus avec un timeout de 25 ms chacun ; la médiane filtre un écho aberrant. Deux échos cohérents au minimum sont requis. Une mesure absente produit `null`.
- `hauteur_plante` : `SENSOR_HEIGHT_CM - distance_plante`. Régler `SENSOR_HEIGHT_CM` après avoir mesuré la distance capteur–base du pot. Si le résultat est négatif, il est envoyé comme `null`.
- `servo` : 0° sous 26 °C, 45° de 26 à moins de 28 °C, 90° dès 28 °C. Commande envoyée seulement quand la position change.
- `ventilateur` : PWM 0 sous 28 °C, 150 de 28 à 30 °C inclus, 255 au-dessus. Si le DHT échoue, le ventilateur s'arrête et la trappe garde sa dernière position.
- `eclairage` / `lighting` : la LED sur D4 suit les ordres du Raspberry Pi. La Yún renvoie son état 0/1 ; le Pi décide automatiquement selon A0 ou reçoit une commande manuelle du site. Sans réponse du Pi, la LED conserve son dernier état.

L'USB envoie un JSON plat facile à lire avec `json.loads()`. L'envoi Wi-Fi garde la structure `sensor` / `readings` comprise par l'API du Pi et inclut les quatre nouvelles mesures. Le backend les enregistre et le panneau « Croissance et aération » les affiche. Si une requête Wi-Fi prend plus de deux secondes, la suivante est ignorée ; la ligne USB continue d'être émise.

Les ordres de servo déjà fournis par le Pi sont aussi lus dans la réponse HTTP. Après un ordre manuel, le servo conserve l'angle demandé pendant 30 secondes, puis reprend la régulation selon la température. L'identifiant de l'ordre est confirmé dans l'envoi suivant.

## Compilation et téléversement

Bibliothèques nécessaires : **DHT sensor library** (Adafruit), **Adafruit Unified Sensor** (dépendance du DHT), **Bridge** et **Servo**. Elles sont présentes sur ce PC ; `Servo` se trouve dans `AppData/Local/Arduino15/libraries`.

Dans Arduino IDE : choisir **Arduino Yún**, sélectionner son port USB, ouvrir `SpaceFarm_Yun_WiFi.ino`, cliquer **Vérifier**, puis **Téléverser**. Ouvrir ensuite le moniteur série à **115200 bauds**. Débrancher ou isoler le moteur et le servo lors du premier téléversement si leur alimentation n'est pas encore vérifiée.

En ligne de commande sur ce PC :

```powershell
& 'C:\Users\yusuk\AppData\Local\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe' compile --fqbn arduino:avr:yun --libraries 'C:\Users\yusuk\AppData\Local\Arduino15\libraries' 'C:\Users\yusuk\Downloads\spacefarm\arduino\SpaceFarm_Yun_WiFi'
```

Pour téléverser par USB une fois le câblage vérifié, sélectionner le port affiché dans Arduino IDE (anciennement COM4) et utiliser **Téléverser**. La compilation seule n'active aucun actionneur.
