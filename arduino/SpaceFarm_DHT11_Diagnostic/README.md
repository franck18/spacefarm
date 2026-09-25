# Diagnostic DHT11 sur Yún

Ce programme teste uniquement le DHT11 par USB. Il ne configure ni Wi-Fi,
ni Raspberry Pi, ni actionneur. Les erreurs ne permettent pas, seules,
de distinguer un mauvais câblage d'un capteur défectueux.

## Avant le téléversement

Débrancher l'alimentation pour modifier le câblage. Grille du DHT11 face à
soi et pattes vers le bas, de gauche à droite : 1 vers 5V, 2 vers D2,
3 non connectée, 4 vers GND. Ajouter 10 kΩ entre 1 et 2.
Le câblage des photos n'est pas validé : ne pas téléverser avant correction.

## Utilisation

1. Ouvrir SpaceFarm_DHT11_Diagnostic.ino dans Arduino IDE.
2. Installer « DHT sensor library » par Adafruit et sa dépendance
   « Adafruit Unified Sensor » via le gestionnaire de bibliothèques.
3. Choisir Arduino Yún et le port détecté (COM4 lors de la préparation).
4. Téléverser : cela remplace le sketch actuel, sans modifier Linux sur la Yún.
5. Ouvrir le moniteur série à 9600 bauds et attendre quelques secondes.

Une ligne JSON arrive toutes les deux secondes, avec température en °C,
humidité relative en %, compteur de tentatives et lectures réussies.
`status: ok` signifie une lecture décodée avec succès ; `status: error`
signifie une lecture échouée et les mesures sont alors `null`.
Aucune valeur d'eau ou de luminosité n'est inventée.

La compilation seule ne valide pas le fonctionnement physique du capteur.
Référence : https://github.com/adafruit/DHT-sensor-library
