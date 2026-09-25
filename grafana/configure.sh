#!/bin/sh
# À lancer sur le Pi après installation de Grafana et du plugin Infinity.
set -eu
cd "$(dirname "$0")"
if ! sudo test -s /etc/grafana/spacefarm-smtp-password; then
    echo "Configurer le mot de passe SMTP dans /etc/grafana/spacefarm-smtp-password avant le déploiement."
    exit 1
fi
sudo cp -n /etc/grafana/grafana.ini /etc/grafana/grafana.ini.before-spacefarm
sudo install -m 640 -o root -g grafana grafana.ini /etc/grafana/grafana.ini
sudo install -d -o grafana -g grafana /var/lib/grafana/dashboards
sudo install -m 644 spacefarm.json /var/lib/grafana/dashboards/spacefarm.json
sudo install -m 644 datasource.yaml /etc/grafana/provisioning/datasources/spacefarm.yaml
sudo install -m 644 provider.yaml /etc/grafana/provisioning/dashboards/spacefarm.yaml
sudo install -m 640 -o root -g grafana alerts.json /etc/grafana/provisioning/alerting/spacefarm.json
# Le mot de passe est créé une seule fois et reste hors du projet.
sudo python3 - <<'PY'
import os
import pwd
import secrets
from pathlib import Path
path = Path('/etc/grafana/spacefarm-admin-password')
if not path.exists():
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    with os.fdopen(fd, 'w') as out:
        out.write(secrets.token_urlsafe(24))
    os.chown(path, 0, pwd.getpwnam('grafana').pw_gid)
PY
sudo mkdir -p /etc/systemd/system/grafana-server.service.d
printf '[Service]\nEnvironment=GOMEMLIMIT=220MiB\nEnvironment=GOMAXPROCS=2\n' | sudo tee /etc/systemd/system/grafana-server.service.d/spacefarm.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl restart grafana-server
