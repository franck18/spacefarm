# Téléverser depuis le Raspberry Pi

Le câble micro-USB de la Yún se branche sur un port USB du Raspberry.
Le Pi compile puis téléverse par USB. Les mesures et les ordres de la LED
continuent de passer par le Wi-Fi entre la Yún et l'API du Pi.

Sur le Raspberry, ouvrir un terminal :

```sh
bash /home/pi/spacefarm/arduino/televerser.sh
```

Le programme à modifier est :
`/home/pi/spacefarm/arduino/SpaceFarm_Yun_WiFi/SpaceFarm_Yun_WiFi.ino`.

Le script compile pour `arduino:avr:yun`, avec un seul processus pour ménager
la mémoire du Pi 3, archive le sketch et son fichier HEX dans `arduino/versions`,
puis téléverse avec vérification de la mémoire écrite.
Il s'arrête en cas d'erreur de compilation et ne téléverse jamais au démarrage.
Le programme reste en mémoire sur la Yún après débranchement : il n'est pas
nécessaire de le téléverser à chaque mise sous tension.

Outils : Arduino CLI, plateforme Arduino AVR Boards, bibliothèques Bridge,
DHT sensor library, Adafruit Unified Sensor et Servo.

Le fonctionnement des capteurs, de la LED, du dashboard, de Grafana et des e-mails
ne nécessite pas le PC. Le Pi et la Yún doivent être alimentés ; le Wi-Fi doit
rester disponible, et l'envoi Gmail exige Internet. Un éventuel assistant IA
relayé par le PC est une fonction séparée et n'est pas migré par ce script.
