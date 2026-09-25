"""Requêtes HTTP : réception des mesures et lecture du tableau de bord."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
import hmac
import json
import mimetypes
from pathlib import Path
import socket
import sys
import time
from urllib.parse import parse_qs, unquote, urlsplit

import db
import ai_proxy
import automation
import commands
from system_info import system_info
from calibration import relative_light, reservoir_level

STARTED = time.time()
MAX_BODY = 64 * 1024  # Taille maximale du JSON reçu.


class Handler(BaseHTTPRequestHandler):
    """Reçoit les mesures et sert le tableau de bord."""
    server_version = 'SpaceFarm/0.3'
    sys_version = ''

    def __init__(self, *args, static_dir=None, config=None, **kwargs):
        self.static_dir = Path(static_dir).resolve() if static_dir else None
        self.config = config or {}
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Dirige chaque envoi vers sa fonction."""
        path = unquote(urlsplit(self.path).path)
        if path == '/api/ingest':
            self._receive_measurements()
        elif path in ('/api/mode', '/api/actuators'):
            self._control_lighting(path)
        elif path.startswith('/api/assistant/'):
            self._ask_assistant(path)
        else:
            self.close_connection = True
            self.json_response(409, {'error': 'Action non disponible.'})

    def _ask_assistant(self, path):
        """Transmet une question et les mesures réelles au relais du PC."""
        try:
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise db.IngestError('Objet JSON attendu.')
            action = path.rsplit('/', 1)[-1]
            if action == 'ask':
                # Les mesures viennent du Pi, jamais du navigateur.
                current = snapshot(self.config)
                payload = {'question': payload.get('question'), 'measurements': {
                    'observedAt': current['observedAt'], 'readings': current['measurements'],
                    'pump': current['pump'], 'lighting': current['lighting']}}
            status, result = ai_proxy.forward(action, payload, self.headers.get('X-SpaceFarm-Code', ''))
            self.json_response(status, result)
        except db.IngestError as error:
            self.json_response(400, {'error': str(error)})

    def _control_lighting(self, path):
        """Change le mode ou la consigne de la LED."""
        try:
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise db.IngestError('Objet JSON attendu.')
            current = snapshot(self.config)
            if not current['system']['controlsAvailable']:
                self.json_response(409, {'error': 'LED de la Yún indisponible.'})
                return
            if path == '/api/mode':
                mode = payload.get('mode')
                if mode not in ('automatic', 'manual'):
                    raise db.IngestError('Mode invalide.')
                automation.set_mode(self.config['db'], mode, current['lighting'])
            else:
                if payload.get('actuator') != 'lighting' or not isinstance(payload.get('enabled'), bool):
                    self.json_response(409, {'error': 'Seule la LED est commandable.'})
                    return
                automation.set_manual_target(self.config['db'], payload['enabled'])
                commands.queue(self.config['db'], automation.YUN_SENSOR, 'lighting',
                               int(payload['enabled']))
            self.json_response(200, snapshot(self.config))
        except (db.IngestError, ValueError) as error:
            self.json_response(400, {'error': str(error)})

    def _receive_measurements(self):
        """Vérifie, enregistre, puis répond à la Yún."""
        try:
            # Lire les mesures envoyées par la Yún.
            payload = self._read_json()
            if not self._authorised(payload):
                self.json_response(401, {'error': 'Jeton absent ou invalide.'})
                return
            # Vérifier le format et les valeurs.
            parsed = db.parse_payload(payload)
            # Enregistrer les mesures dans SQLite.
            alerts = db.store_readings(self.config['db'], *parsed)
        except db.IngestError as error:
            self.json_response(400, {'error': str(error)})
            return
        except Exception as error:  # Répondre même si la base échoue.
            self.log_message('erreur ingestion: %s', error)
            self.json_response(500, {'error': 'Écriture impossible.'})
            return
        # Confirmer la réception à la Yún. L'ordre en attente voyage dans cette
        # réponse, en premier champ : la carte n'a que peu de mémoire pour la lire.
        try:
            commands.confirm(self.config['db'], parsed[0], payload.get('ack'))
            automation.reconcile(self.config['db'], parsed[0], parsed[5])
            command = commands.encode(commands.take(self.config['db'], parsed[0]))
        except Exception as error:  # Les mesures sont déjà enregistrées ; l'ordre attendra.
            self.log_message('erreur ordres: %s', error)
            command = ''
        self.json_response(201, {'command': command, 'status': 'ok', 'sensor': parsed[0],
                                 'stored': len(parsed[5]), 'alerts': alerts})

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise db.IngestError('En-tête Content-Length invalide.')
        if length <= 0:
            raise db.IngestError('Corps de requête vide.')
        if length > MAX_BODY:
            raise db.IngestError('Corps de requête trop volumineux ({} octets max).'.format(MAX_BODY))
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise db.IngestError('JSON illisible.')

    def _authorised(self, payload):
        """Jeton partagé optionnel. Comparaison à temps constant."""
        expected = self.config.get('token')
        if not expected:
            return True
        supplied = self.headers.get('X-Auth-Token') or (payload or {}).get('token') or ''
        return hmac.compare_digest(str(supplied), expected)

    def do_GET(self):
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)

        if path == '/api/state':
            self.json_response(200, snapshot(self.config))
            return
        if path == '/api/health':
            self.json_response(200, {'status': 'ok', 'hostname': socket.gethostname(),
                                     'service': 'spacefarm', 'version': '0.3.0',
                                     'uptimeSeconds': round(time.time() - STARTED, 1)})
            return
        if path == '/api/metrics':
            self.json_response(200, {'metrics': db.all_metrics(self.config['db'],
                                                               stale_after_s=self.config['stale'])})
            return
        if path == '/api/sensors':
            self.json_response(200, {'sensors': db.sensors(self.config['db'],
                                                           stale_after_s=self.config['stale'])})
            return
        if path == '/api/stats':
            self.json_response(200, db.stats(self.config['db']))
            return
        if path == '/api/history':
            try:
                hours = min(168.0, max(0.1, float(query.get('hours', ['6'])[0])))
                points = min(1000, max(10, int(query.get('points', ['180'])[0])))
            except ValueError:
                self.json_response(400, {'error': 'Paramètres « hours » ou « points » invalides.'})
                return
            metrics = query.get('metric') or list(db.DASHBOARD_METRICS)
            self.json_response(200, {'history': db.history(self.config['db'], metrics=metrics,
                                                           hours=hours, points=points)})
            return

        if self.static_dir is None or path.startswith('/api/'):
            self.json_response(404, {'error': 'Ressource introuvable.'})
            return
        try:
            target = (self.static_dir / (path.lstrip('/') or 'index.html')).resolve()
            if self.static_dir not in target.parents or not target.is_file():
                self.json_response(404, {'error': 'Ressource introuvable.'})
                return
            content_type = {'.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml'}.get(target.suffix)
            content_type = content_type or mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
            self.send_body(200, target.read_bytes(), content_type)
        except (OSError, ValueError):
            self.json_response(404, {'error': 'Ressource introuvable.'})

    def do_HEAD(self):
        self.do_GET()

    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def json_response(self, status, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode('utf-8')
        self.send_body(status, body, 'application/json; charset=utf-8')

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


def percent_reading(reading, convert):
    """Garde la date et la qualité de la mesure convertie en %."""
    value = convert(reading['value'])
    quality = reading['quality'] if value is not None else 'error'
    return dict(reading, value=value, unit='%', quality=quality)


def snapshot(config):
    """Construit la réponse /api/state à partir de la base."""
    observed_at = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    # Lire les dernières valeurs une seule fois, puis préparer les cartes.
    crop_metrics = ('distance_plante', 'hauteur_plante', 'servo', 'ventilateur')
    raw = db.latest_measurements(
        config['db'],
        metrics=('temperature', 'humidity', 'light_raw', 'water_raw', 'lighting') + crop_metrics,
        stale_after_s=config['stale'])
    measurements = {
        'temperature': raw['temperature'],
        'humidity': raw['humidity'],
        'light': percent_reading(raw['light_raw'], relative_light),
        'water': percent_reading(raw['water_raw'], reservoir_level),
    }
    cultivation = {name: raw[name] for name in crop_metrics}
    led = raw['lighting']
    lighting = bool(led['value']) if led['quality'] == 'ok' and led['value'] in (0, 1) else None
    system = system_info()
    system['controlsAvailable'] = lighting is not None
    history = db.history(config['db'], metrics=('temperature', 'humidity', 'light_raw', 'water_raw'),
                         hours=config['history_hours'])
    for point in history:
        point['light'] = relative_light(point.pop('light_raw'))
        point['water'] = reservoir_level(point.pop('water_raw'))
    live = any(m['quality'] == 'ok' and m['value'] is not None for m in measurements.values())

    water = measurements.get('water', {})
    reservoir_capacity = config['reservoir']
    reservoir_liters = None
    if water.get('quality') == 'ok' and water.get('value') is not None:
        reservoir_liters = round(reservoir_capacity * water['value'] / 100, 4)

    return {
        'schemaVersion': 1,
        'source': 'live',
        'observedAt': observed_at,
        # Indique si des mesures récentes sont disponibles.
        'mode': automation.settings(config['db'])[0] if live else 'unconfigured',
        'measurements': measurements,
        'cultivation': cultivation,
        'pump': None, 'lighting': lighting, 'actuatorFeedback': 'measured' if live else 'unavailable',
        'reservoirLiters': reservoir_liters, 'reservoirCapacity': reservoir_capacity,
        'scenario': {'active': False, 'referenceLiters': None, 'fraction': 1},
        'system': system,
        'history': history,
        'events': db.recent_events(config['db']),
    }
