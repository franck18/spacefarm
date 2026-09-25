# Conception FreeCAD SpaceFarm 2080

Le modèle est divisé en cinq pièces indépendantes : un socle Arduino Yún avec
rails de breadboard, un boîtier ouvert et ventilé pour Raspberry Pi 3, un
support protégé pour DHT11, un support orientable pour le capteur de lumière et
une pince de réservoir pour la sonde d’eau.

Cette organisation permet de réimprimer un seul élément lorsqu’une mesure
change. Les cartes restent accessibles et le DHT11 reste en contact avec l’air.
La pince maintient uniquement la zone électronique de la sonde au-dessus de
l’eau ; sa profondeur doit être réglée lors du montage.

Le script `cad/SpaceFarm_2080.py` contient les dimensions modifiables au début.
Les dimensions standards du Raspberry Pi 3 et de l’Arduino Yún servent de base.
La breadboard, l’épaisseur de la paroi du réservoir et les modules capteurs
doivent être mesurés avant l’impression finale.

Paramètres d’impression conseillés : PLA ou PETG, buse 0,4 mm, couche 0,2 mm,
trois parois, 20 % de remplissage. Les pièces sont dessinées avec une épaisseur
minimale de 2,4 mm et un jeu nominal de 0,4 mm.
