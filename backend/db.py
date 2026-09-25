"""Vérifie, enregistre et relit les mesures dans SQLite."""
from contextlib import contextmanager
from datetime import datetime, timezone
import math
import re
import sqlite3
import sys
import time

SCHEMA_VERSION = 1

# Les 4 métriques que le dashboard actuel sait afficher, dans l'ordre d'affichage.
DASHBOARD_METRICS = ('temperature', 'humidity', 'light', 'water')

# Unité retenue si le capteur n'en déclare pas.
DEFAULT_UNITS = {
    'temperature': '°C', 'humidity': '%', 'light': 'lx', 'water': '%', 'ph': 'pH',
    'conductivity': 'µS/cm', 'co2': 'ppm', 'power': 'W', 'battery': '%', 'solar': 'W',
    'voltage': 'V', 'current': 'A',
}

# Bornes de bon fonctionnement, alignées sur celles codées dans le frontend.
NOMINAL_RANGE = {
    'temperature': (18.0, 28.0), 'humidity': (45.0, 75.0),
    'light': (0.0, 1000.0), 'water': (20.0, 100.0),
}

# Bornes d'acceptation du DHT11 utilisé par SpaceFarm.
PLAUSIBLE_RANGE = {
    'temperature': (0.0, 50.0), 'humidity': (20.0, 80.0), 'light': (0.0, 200000.0),
    'water': (0.0, 100.0), 'ph': (0.0, 14.0), 'battery': (0.0, 100.0),
}

METRIC_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
SENSOR_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$')
QUALITIES = ('ok', 'warning', 'error')
KINDS = ('info', 'success', 'warning', 'error')

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Registre des cartes : une ligne par ESP32/Arduino qui a déjà parlé au Pi.
CREATE TABLE IF NOT EXISTS sensors (
    sensor_id  TEXT PRIMARY KEY,
    pillar     TEXT NOT NULL DEFAULT 'foodtech',
    label      TEXT,
    location   TEXT,
    first_seen INTEGER NOT NULL,
    last_seen  INTEGER NOT NULL
);

-- Série temporelle : une ligne = une mesure d'une métrique à un instant donné.
CREATE TABLE IF NOT EXISTS readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id   TEXT    NOT NULL REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    metric      TEXT    NOT NULL,
    value       REAL,
    unit        TEXT,
    quality     TEXT    NOT NULL DEFAULT 'ok',
    observed_at INTEGER NOT NULL,
    received_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_readings_metric_time ON readings(metric, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON readings(sensor_id, observed_at DESC);

-- Journal affiché dans le dashboard (alertes seuil, arrivée d'une carte, etc.).
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    kind      TEXT    NOT NULL,
    message   TEXT    NOT NULL,
    sensor_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp DESC);
"""


class IngestError(ValueError):
    """Charge utile refusée : le message est renvoyé tel quel au capteur."""


def now_ms():
    return int(time.time() * 1000)


@contextmanager
def session(path):
    """Ouvre une connexion configurée et garantit sa fermeture."""
    conn = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=5000')
        conn.execute('PRAGMA foreign_keys=ON')
        yield conn
    finally:
        conn.close()


def initialise(path):
    """Crée le schéma si besoin. Idempotent : peut tourner à chaque démarrage."""
    with session(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute('INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
                     ('schema_version', str(SCHEMA_VERSION)))


# --- Écriture ---------------------------------------------------------------

def _coerce_value(metric, raw):
    """Valide une valeur brute. Renvoie (valeur, qualité) ; None reste None."""
    if raw is None:
        return None, 'error'
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise IngestError('Valeur non numérique pour « {} ».'.format(metric))
    value = float(raw)
    if not math.isfinite(value):
        raise IngestError('Valeur non finie pour « {} ».'.format(metric))
    low, high = PLAUSIBLE_RANGE.get(metric, (-1e12, 1e12))
    if not low <= value <= high:
        # Hors plage physique : on garde la trace mais on la marque comme fausse.
        return round(value, 4), 'error'
    return round(value, 4), 'ok'


def parse_payload(payload):
    """Transforme le JSON reçu en (sensor_id, pillar, label, location, observed_at, relevés).

    Deux écritures acceptées pour un relevé :
        "temperature": 23.4
        "temperature": {"value": 23.4, "unit": "°C", "quality": "ok"}
    """
    if not isinstance(payload, dict):
        raise IngestError('Le corps doit être un objet JSON.')

    sensor_id = payload.get('sensor') or payload.get('sensorId')
    if not isinstance(sensor_id, str) or not SENSOR_PATTERN.match(sensor_id):
        raise IngestError('Champ « sensor » manquant ou invalide (alphanumérique, 48 max).')

    readings = payload.get('readings')
    if not isinstance(readings, dict) or not readings:
        raise IngestError('Champ « readings » manquant ou vide.')
    if len(readings) > 32:
        raise IngestError('Trop de métriques dans un même envoi (32 maximum).')

    observed_at = payload.get('observedAt')
    if observed_at is None:
        observed_at = now_ms()
    elif isinstance(observed_at, (int, float)) and not isinstance(observed_at, bool):
        observed_at = int(observed_at)
    else:
        raise IngestError('Champ « observedAt » invalide (millisecondes epoch attendues).')

    # Une carte sans horloge envoie 0 ou un compteur depuis le boot : on recale sur le Pi.
    current = now_ms()
    if not (current - 86_400_000) < observed_at <= (current + 300_000):
        observed_at = current

    entries = []
    for metric, raw in readings.items():
        if not isinstance(metric, str) or not METRIC_PATTERN.match(metric):
            raise IngestError('Nom de métrique invalide : « {} ».'.format(metric)[:120])
        unit, quality_hint = None, None
        if isinstance(raw, dict):
            unit = raw.get('unit') if isinstance(raw.get('unit'), str) else None
            quality_hint = raw.get('quality') if raw.get('quality') in QUALITIES else None
            raw = raw.get('value')
        value, quality = _coerce_value(metric, raw)
        entries.append({
            'metric': metric, 'value': value,
            'unit': (unit or DEFAULT_UNITS.get(metric) or '')[:16],
            'quality': quality_hint or quality,
        })

    pillar = payload.get('pillar') if payload.get('pillar') in ('foodtech', 'energytech') else 'foodtech'
    label = payload.get('label') if isinstance(payload.get('label'), str) else None
    location = payload.get('location') if isinstance(payload.get('location'), str) else None
    return sensor_id, pillar, (label or '')[:64] or None, (location or '')[:64] or None, observed_at, entries


def store_readings(path, sensor_id, pillar, label, location, observed_at, entries):
    """Insère un lot de relevés et renvoie la liste des alertes de seuil déclenchées."""
    received_at = now_ms()
    with session(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            known = conn.execute('SELECT sensor_id FROM sensors WHERE sensor_id = ?',
                                 (sensor_id,)).fetchone()
            if known is None:
                conn.execute(
                    'INSERT INTO sensors(sensor_id, pillar, label, location, first_seen, last_seen)'
                    ' VALUES (?, ?, ?, ?, ?, ?)',
                    (sensor_id, pillar, label, location, received_at, received_at))
                _insert_event(conn, received_at, 'success',
                              'Nouveau capteur enregistré · {}'.format(sensor_id), sensor_id)
            else:
                conn.execute(
                    'UPDATE sensors SET last_seen = ?, pillar = ?,'
                    ' label = COALESCE(?, label), location = COALESCE(?, location)'
                    ' WHERE sensor_id = ?',
                    (received_at, pillar, label, location, sensor_id))

            # Ajouter une ligne par mesure.
            conn.executemany(
                'INSERT INTO readings(sensor_id, metric, value, unit, quality, observed_at, received_at)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                [(sensor_id, e['metric'], e['value'], e['unit'], e['quality'], observed_at, received_at)
                 for e in entries])

            alerts = _threshold_alerts(conn, sensor_id, entries, received_at)
            # Valider tout le lot.
            conn.execute('COMMIT')
            return alerts
        except Exception:
            conn.execute('ROLLBACK')
            raise


def _threshold_alerts(conn, sensor_id, entries, timestamp):
    """Journalise une alerte quand une mesure sort de sa plage nominale.

    L'alerte n'est écrite qu'au franchissement du seuil, pas à chaque relevé :
    sinon le journal se remplit d'une ligne identique toutes les 10 secondes.
    """
    alerts = []
    for entry in entries:
        metric, value, quality = entry['metric'], entry['value'], entry['quality']
        if quality != 'ok' or value is None or metric not in NOMINAL_RANGE:
            continue
        low, high = NOMINAL_RANGE[metric]
        outside = value < low or value > high
        previous = conn.execute(
            'SELECT value FROM readings WHERE sensor_id = ? AND metric = ? AND quality = "ok"'
            ' AND value IS NOT NULL ORDER BY observed_at DESC, id DESC LIMIT 1 OFFSET 1',
            (sensor_id, metric)).fetchone()
        was_outside = previous is not None and not (low <= previous['value'] <= high)
        if outside and not was_outside:
            message = '{} hors plage · {} {} (attendu {}–{})'.format(
                metric, value, entry['unit'], low, high)
            _insert_event(conn, timestamp, 'warning', message, sensor_id)
            alerts.append(message)
        elif not outside and was_outside:
            message = '{} revenu dans la plage nominale · {} {}'.format(metric, value, entry['unit'])
            _insert_event(conn, timestamp, 'success', message, sensor_id)
            alerts.append(message)
    return alerts


def _insert_event(conn, timestamp, kind, message, sensor_id=None):
    conn.execute('INSERT INTO events(timestamp, kind, message, sensor_id) VALUES (?, ?, ?, ?)',
                 (timestamp, kind if kind in KINDS else 'info', message[:240], sensor_id))


def record_event(path, kind, message, sensor_id=None):
    with session(path) as conn:
        _insert_event(conn, now_ms(), kind, message, sensor_id)


def purge(path, retention_days=7, max_events=500):
    """Borne la taille de la base : la carte SD du Pi n'est pas extensible."""
    cutoff = now_ms() - retention_days * 86_400_000
    with session(path) as conn:
        deleted = conn.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount
        conn.execute('DELETE FROM events WHERE id NOT IN'
                     ' (SELECT id FROM events ORDER BY timestamp DESC, id DESC LIMIT ?)',
                     (max_events,))
        return deleted


# --- Lecture ----------------------------------------------------------------

def latest_measurements(path, metrics=DASHBOARD_METRICS, stale_after_s=120):
    """Dernière valeur connue de chaque métrique, au format attendu par le dashboard.

    Une mesure plus vieille que `stale_after_s` repasse en qualité « error » : mieux vaut
    un capteur affiché indisponible qu'une valeur périmée présentée comme vraie.
    """
    current = now_ms()
    stale_ms = stale_after_s * 1000
    result = {}
    with session(path) as conn:
        for metric in metrics:
            row = conn.execute(
                'SELECT value, unit, quality, observed_at FROM readings'
                ' WHERE metric = ? ORDER BY observed_at DESC, id DESC LIMIT 1',
                (metric,)).fetchone()
            if row is None:
                result[metric] = {'value': None, 'quality': 'error', 'observedAt': _iso(current)}
                continue
            quality = row['quality']
            if current - row['observed_at'] > stale_ms:
                quality = 'error'
            result[metric] = {
                # Masquer les valeurs invalides sans effacer l'historique.
                'value': None if quality == 'error' else row['value'],
                'quality': quality,
                'observedAt': _iso(row['observed_at']),
            }
    return result


def history(path, metrics=DASHBOARD_METRICS, hours=6, points=180):
    """Série temporelle agrégée, en lignes larges : {timestamp, temperature, humidity, ...}.

    L'agrégation se fait en SQL (moyenne par tranche de temps) plutôt qu'en Python :
    un relevé toutes les 10 s sur 6 h fait 2160 lignes par métrique, et le Pi n'a pas
    à les transporter pour n'en afficher que 180.
    """
    safe = [m for m in metrics if METRIC_PATTERN.match(m)]
    if not safe:
        return []
    since = now_ms() - int(hours * 3_600_000)
    bucket = max(1000, int(hours * 3_600_000 / max(1, points)))
    # Les noms de métriques sont validés par METRIC_PATTERN avant interpolation.
    columns = ', '.join(
        'ROUND(AVG(CASE WHEN metric = \'{0}\' AND quality = \'ok\' THEN value END), 3) AS {0}'.format(m)
        for m in safe)
    query = (
        'SELECT (observed_at / ?) * ? AS bucket, {}'
        ' FROM readings WHERE observed_at >= ?'
        ' GROUP BY bucket ORDER BY bucket ASC'.format(columns))
    with session(path) as conn:
        rows = conn.execute(query, (bucket, bucket, since)).fetchall()
    return [dict({'timestamp': row['bucket']}, **{m: row[m] for m in safe}) for row in rows]


def recent_events(path, limit=40):
    with session(path) as conn:
        rows = conn.execute(
            'SELECT id, timestamp, kind, message FROM events'
            ' ORDER BY timestamp DESC, id DESC LIMIT ?', (limit,)).fetchall()
    return [{'id': 'evt-{}'.format(r['id']), 'timestamp': r['timestamp'],
             'kind': r['kind'], 'message': r['message']} for r in rows]


def all_metrics(path, stale_after_s=120):
    """Toutes les métriques stockées, y compris celles qu'aucun panneau n'affiche encore.

    C'est le point d'entrée pour le pilier Énergie : les relevés arrivent et sont
    conservés dès maintenant, même si l'interface ne les trace pas encore.
    """
    current = now_ms()
    with session(path) as conn:
        rows = conn.execute(
            'SELECT r.metric, r.value, r.unit, r.quality, r.observed_at, r.sensor_id, s.pillar'
            ' FROM readings r JOIN sensors s ON s.sensor_id = r.sensor_id'
            ' JOIN (SELECT metric, MAX(observed_at) AS peak FROM readings GROUP BY metric) last'
            '   ON last.metric = r.metric AND last.peak = r.observed_at'
            ' GROUP BY r.metric ORDER BY s.pillar, r.metric').fetchall()
    return [{'metric': r['metric'], 'value': r['value'], 'unit': r['unit'],
             'quality': 'error' if current - r['observed_at'] > stale_after_s * 1000 else r['quality'],
             'observedAt': _iso(r['observed_at']), 'sensor': r['sensor_id'], 'pillar': r['pillar']}
            for r in rows]


def sensors(path, stale_after_s=120):
    current = now_ms()
    with session(path) as conn:
        rows = conn.execute(
            'SELECT s.sensor_id, s.pillar, s.label, s.location, s.first_seen, s.last_seen,'
            ' (SELECT COUNT(*) FROM readings r WHERE r.sensor_id = s.sensor_id) AS samples'
            ' FROM sensors s ORDER BY s.sensor_id').fetchall()
    return [{'sensor': r['sensor_id'], 'pillar': r['pillar'], 'label': r['label'],
             'location': r['location'], 'samples': r['samples'],
             'online': (current - r['last_seen']) <= stale_after_s * 1000,
             'firstSeen': _iso(r['first_seen']), 'lastSeen': _iso(r['last_seen'])} for r in rows]


def stats(path):
    with session(path) as conn:
        row = conn.execute(
            'SELECT (SELECT COUNT(*) FROM readings) AS readings,'
            ' (SELECT COUNT(*) FROM sensors) AS sensors,'
            ' (SELECT COUNT(DISTINCT metric) FROM readings) AS metrics,'
            ' (SELECT MIN(observed_at) FROM readings) AS oldest,'
            ' (SELECT MAX(observed_at) FROM readings) AS newest').fetchone()
    return {'readings': row['readings'], 'sensors': row['sensors'], 'metrics': row['metrics'],
            'oldest': _iso(row['oldest']) if row['oldest'] else None,
            'newest': _iso(row['newest']) if row['newest'] else None}


def _iso(epoch_ms):
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def purge_loop(config):
    """Supprime chaque heure les mesures trop anciennes."""
    while True:
        time.sleep(3600)
        try:
            removed = purge(config['db'], retention_days=config['retention'])
            if removed:
                print('Purge : {} relevés supprimés (> {} jours)'.format(removed, config['retention']),
                      flush=True)
        except Exception as error:  # Le serveur continue en cas d’échec.
            print('Purge impossible : {}'.format(error), file=sys.stderr, flush=True)
