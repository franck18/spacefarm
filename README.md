# SpaceFarm 2080

Interface du workshop EPSI Bachelor 3, pilier FoodTech & AgriTech.

## État du dépôt - 25 septembre 2026

Ce dépôt rassemble le code et les documents présents sur le PC : frontend React,
API Python/SQLite, sketch Arduino Yún, configuration Grafana et alertes e-mail,
conception FreeCAD, présentation, PDF, photos et vidéo du prototype.
Les dépendances installées, secrets, bases de mesures et sauvegardes intermédiaires
ne sont pas versionnés. Les bibliothèques frontend se réinstallent avec `npm ci`.

- La Yún transmet les mesures au Pi par Wi-Fi. Le Pi peut aussi compiler et
  téléverser le sketch par USB : [guide](arduino/TELEVERSER_DEPUIS_LE_PI.md).
- Grafana complète le centre de contrôle : [installation et alertes](grafana/README.md).
- Le réservoir déclaré est de **729 mL**. Sa calibration volumétrique reste
  incomplète : le pourcentage de la sonde n'est pas une mesure validée du volume.
- La commande réelle du dashboard concerne la LED ; la pompe n'est pas branchée.
  Les panneaux de croissance, d'aération et de pompe ont été retirés du frontend.
- La simplification locale du code est incluse ; elle n'a pas encore été déployée
  intégralement sur le Pi. Certains documents décrivent des objectifs initiaux
  ou des versions antérieures du prototype.
- Les mots de passe Grafana et Gmail ne sont pas inclus. Les chemins de secrets
  dans les fichiers de configuration sont à renseigner sur le Pi de destination.

Le [PDF actualisé](output/pdf/SpaceFarm_Cahier_des_charges_actualise.pdf) contient
le bilan de la supervision et des alertes e-mail.

## Accès au Raspberry Pi

Accès Wi-Fi : **http://192.168.41.88:8000/** sur le réseau du lycée. Cette adresse DHCP peut changer. Le service écoute sur toutes les interfaces IPv4 ; l'interface et les commandes de la LED sont accessibles aux appareils pouvant joindre le Pi, sans authentification côté tableau de bord.

Le Pi héberge l'interface, l'API et la base SQLite. Le service `spacefarm.service` démarre automatiquement.

L'état du Pi et les mesures envoyées par l'Arduino Yún sont réels : DHT11, photorésistance, niveau d'eau et ultrason. Le Pi commande la LED selon la luminosité en mode automatique, ou depuis le tableau de bord en mode manuel. La pompe n'est pas branchée. Le lien **Mode démo** donne accès à la simulation ; **Connecter au Pi** revient aux données réelles. Le radis a été remplacé par la tomate (besoins toujours théoriques).

Voir [le guide de connexion et d’exploitation](docs/api.md).

## Lancer l’interface sur Windows

Prérequis : Node.js 22.12+ (ou 24 LTS) et npm.

```powershell
cd C:\Users\yusuk\Downloads\spacefarm\frontend
npm.cmd install
npm.cmd run dev
```

Ouvrir http://127.0.0.1:5180. Le serveur écoute uniquement sur le PC par défaut. Le port 5180 évite le conflit avec une autre application déjà présente sur le PC.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`build` vérifie TypeScript puis génère `frontend/dist/`. `preview` sert ce résultat pour vérification locale. Aucun compte ni accès Internet n’est nécessaire après installation : les polices sont embarquées.

## Ce qui fonctionne en mode démonstration

- Tableau de bord responsive, quatre mesures actualisées toutes les 3 secondes.
- Historique synthétique sur 24 h, sélection de mesure et de période, statistiques et infobulles.
- Mode automatique simulé : pompe 8 s par cycle de 120 s, éclairage actif.
- Mode manuel : commandes simulées de pompe et d’éclairage. Pompe limitée à 10 s lors du prochain rafraîchissement ; arrêt si réserve inférieure à 15 %.
- Scénario de crise séparé : 40 % de la réserve au démarrage du scénario ; allocations prioritaires ; calcul d’objectif 48 h.
- Journal filtrable, détail des capteurs, coupure simulée avec commandes désactivées, reprise et réinitialisation.

## Limites explicites

Le mode **démonstration** fonctionne sans commander le matériel et sans contacter le Pi ; son historique est synthétique. La vue **Raspberry Pi** lit les mesures enregistrées dans SQLite et commande uniquement la LED. Les trois cultures et leurs besoins sont des hypothèses pédagogiques, pas des recommandations agronomiques. L'humidité affichée est celle de l'air. La luminosité est relative, en %, et non mesurée en lux.

Le simulateur fonctionne uniquement tant que la page est active : le navigateur peut ralentir ses timers en arrière-plan. Ses limites de pompe ne sont donc pas une protection matérielle. Dans la vue réelle, la décision automatique d'éclairage s'exécute sur le Pi, indépendamment du navigateur.

Le réservoir descend selon une hypothèse de perte nette constante de 0,1 L/h. La pompe représente la circulation de solution ; son activité n’est pas un débitmètre. Les allocations affichées sont théoriques. La crise ne réécrit pas le niveau du réservoir et ne change pas de matériel réel.

## Architecture

`frontend/src/components/` : panneaux visuels. `data/engine.ts` : règles pures de démonstration et budget d’eau. `data/provider.ts` : adaptateurs mock/API. `data/types.ts` : contrat validé avec Zod. `hooks/useSpaceFarm.ts` : acquisition, commandes et état de connexion.

Le backend est dans `backend/` et utilise la bibliothèque standard Python et SQLite. Il reçoit les mesures de la Yún par Wi-Fi, les stocke et renvoie les ordres de LED dans la réponse d'ingestion : voir [docs/api.md](docs/api.md). Pas de remplacement automatique par des mocks en cas d'erreur.

## Dépendances

React/React DOM : interface ; TypeScript : vérification des types ; Vite : développement et compilation ; Recharts : graphiques ; Lucide : icônes ; Fontsource : polices locales ; Zod : validation du contrat API ; Vitest : tests des règles. Les versions résolues sont verrouillées dans `package-lock.json`.

Les PDF du workshop sont conservés à la racine sans modification.
