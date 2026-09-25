# Assistant SpaceFarm

Le Raspberry sert l’interface et les mesures. Le PC exécute `bridge.py` et Codex App Server.
Le Pi 32 bits ne reçoit aucun identifiant ChatGPT. Le PC doit rester allumé.

1. Sur le PC, lancer `python assistant/bridge.py` avec Codex disponible dans PATH.
2. Ouvrir le tunnel : `ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -R 127.0.0.1:8765:127.0.0.1:8765 pi@169.254.82.190`.
3. Ouvrir `http://192.168.41.88:8000/?source=api#assistant`.
4. Saisir le code présent dans `%LOCALAPPDATA%/SpaceFarmAssistant/access-code.txt`.
5. Cliquer sur « Se connecter avec ChatGPT », puis saisir le code d’appareil sur la page officielle.

La session Codex dédiée réside dans `%LOCALAPPDATA%/SpaceFarmAssistant/codex`.
Ne pas partager ce dossier ni le code d’accès. Le dashboard local utilise HTTP : employer
un réseau de confiance ; le tunnel entre Pi et PC est chiffré par SSH.
Les mesures ne sont envoyées à OpenAI qu’après une demande d’analyse.
L’assistant ne dispose d’aucune commande d’actionneur. Chaque analyse est indépendante.
Les outils shell sont désactivés et les sessions Codex sont en lecture seule.

Après redémarrage du PC, relancer le relais et le tunnel. Le bouton Déconnecter révoque
la session locale dédiée sans modifier celle de l’application Codex habituelle.
