# Pièces 3D SpaceFarm

Le script [`SpaceFarm_2080.py`](./SpaceFarm_2080.py) génère :

- le socle Arduino Yún et breadboard ;
- le boîtier ventilé du Raspberry Pi 3 ;
- le support du DHT11 ;
- le support du capteur de lumière ;
- la pince du capteur de niveau d’eau ;
- un peigne pour les câbles Dupont.

## Utilisation

1. Installer FreeCAD.
2. Mesurer la breadboard, le capteur de lumière, la sonde d’eau et la paroi du réservoir.
3. Modifier les constantes marquées `À mesurer` au début du script.
4. Dans FreeCAD : **Vue → Panneaux → Console Python**, puis exécuter :

   ```python
   script = r'C:\Users\yusuk\Downloads\spacefarm\cad\SpaceFarm_2080.py'
   exec(compile(open(script, encoding='utf-8').read(), script, 'exec'), {'__file__': script})
   ```

   En ligne de commande, si `FreeCADCmd` est disponible :

   ```powershell
   FreeCADCmd C:\Users\yusuk\Downloads\spacefarm\cad\SpaceFarm_2080.py
   ```

Les STL et le fichier `SpaceFarm_2080.FCStd` apparaîtront dans `cad/output`.

Avant une impression longue, imprimer seulement quelques couches ou une petite
section pour vérifier l’écartement des vis et l’épaisseur des modules réels.
