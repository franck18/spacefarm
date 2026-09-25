#!/bin/bash
# Compiler et téléverser depuis le Raspberry Pi, sans le PC.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
CLI="$HOME/.local/bin/arduino-cli"
SKETCH="$ROOT/SpaceFarm_Yun_WiFi"
PORT="/dev/serial/by-id/usb-Arduino_LLC_Arduino_Yun-if00"

# Éviter deux téléversements simultanés.
exec 9>"$ROOT/.upload.lock"
flock -n 9 || { echo "Un téléversement est déjà en cours."; exit 1; }
if [[ ! -e "$PORT" ]]; then
    echo "Branche le câble micro-USB de la Yún sur un port USB du Raspberry."
    exit 1
fi

echo "Compilation du programme sur le Raspberry..."
mkdir -p "$ROOT/build"
"$CLI" compile --fqbn arduino:avr:yun --jobs 1 --output-dir "$ROOT/build" "$SKETCH"

# Conserver le programme compilé avant de redémarrer la carte.
ARCHIVE="$ROOT/versions/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARCHIVE"
cp "$SKETCH/SpaceFarm_Yun_WiFi.ino" "$ARCHIVE/"
cp "$ROOT/build/SpaceFarm_Yun_WiFi.ino.hex" "$ARCHIVE/"
echo "Téléversement USB sur la Yún..."
"$CLI" upload --fqbn arduino:avr:yun --port "$(readlink -f "$PORT")" --input-dir "$ROOT/build" --verify "$SKETCH"
echo "Terminé. La Yún redémarre et reprend ses envois Wi-Fi vers le Pi."
