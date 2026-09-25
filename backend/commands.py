"""Transmet un ordre dans la réponse HTTP au prochain relevé de la Yún.

Un nouvel ordre remplace celui en attente pour le même actionneur.
Un ordre non livré expire après 15 s ; le champ ack confirme son application.
Exemple : « lighting 1 42 » = allumer la LED, ordre numéro 42.
"""
import db

TTL_S = 15

# Action -> (actionneur visé, valeur minimale, valeur maximale).
ACTIONS = {
    'pump': ('pump', 1, 30),        # Ancienne commande ; refusée par le dashboard actuel.
    'stop': ('pump', 0, 0),
    'servo': ('servo', 0, 180),     # Angle en degrés.
    'lighting': ('lighting', 0, 1), # LED de la serre.
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS commands (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id    TEXT    NOT NULL,
    action       TEXT    NOT NULL,
    value        INTEGER NOT NULL,
    created_at   INTEGER NOT NULL,
    expires_at   INTEGER NOT NULL,
    delivered_at INTEGER,
    acked_at     INTEGER
)
"""


def queue(path, sensor_id, action, value=0, ttl_s=TTL_S, now=None):
    """Met un ordre en attente pour une carte ; renvoie son identifiant."""
    if action not in ACTIONS:
        raise ValueError('Action inconnue : %s' % action)
    target, low, high = ACTIONS[action]
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError('Valeur hors limites pour %s : %r (%d à %d)' % (action, value, low, high))
    same_target = [name for name, spec in ACTIONS.items() if spec[0] == target]
    now = db.now_ms() if now is None else now
    with db.session(path) as conn:
        conn.execute(SCHEMA)
        conn.execute('BEGIN IMMEDIATE')
        # Seul le dernier ordre visant cet actionneur compte : les précédents expirent.
        conn.execute('UPDATE commands SET expires_at = ? WHERE sensor_id = ? AND delivered_at IS NULL'
                     ' AND expires_at > ? AND action IN (%s)' % ','.join('?' * len(same_target)),
                     [now, sensor_id, now] + same_target)
        cursor = conn.execute(
            'INSERT INTO commands(sensor_id, action, value, created_at, expires_at)'
            ' VALUES (?, ?, ?, ?, ?)', (sensor_id, action, value, now, now + ttl_s * 1000))
        conn.execute('COMMIT')
        return cursor.lastrowid


def take(path, sensor_id, now=None):
    """Livre le plus ancien ordre en attente de cette carte, une seule fois ; None sinon."""
    now = db.now_ms() if now is None else now
    with db.session(path) as conn:
        conn.execute(SCHEMA)
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            'SELECT id, action, value FROM commands WHERE sensor_id = ?'
            ' AND delivered_at IS NULL AND expires_at > ? ORDER BY id LIMIT 1',
            (sensor_id, now)).fetchone()
        if row is not None:
            conn.execute('UPDATE commands SET delivered_at = ? WHERE id = ?', (now, row['id']))
        conn.execute('COMMIT')
    return None if row is None else (row['id'], row['action'], row['value'])


def encode(command):
    """Format compact lu par le croquis : « pump 10 42 », ou « » sans ordre."""
    if command is None:
        return ''
    command_id, action, value = command
    return '%s %d %d' % (action, value, command_id)


def describe(action, value):
    """Libellé pour le journal. Un accusé dit que l'ordre est appliqué, pas qu'il est allé à son terme."""
    if action == 'pump':
        return 'arrosage de %d s lancé' % value
    if action == 'servo':
        return 'servo commandé à %d°' % value
    if action == 'lighting':
        return 'éclairage %s' % ('allumé' if value else 'éteint')
    return 'pompe arrêtée'


def confirm(path, sensor_id, ack, now=None):
    """La carte signale le dernier ordre appliqué ; journalise la confirmation une seule fois."""
    if isinstance(ack, bool) or not isinstance(ack, (int, float)) or ack < 1:
        return False
    now = db.now_ms() if now is None else now
    with db.session(path) as conn:
        conn.execute(SCHEMA)
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            'SELECT action, value FROM commands WHERE id = ? AND sensor_id = ?'
            ' AND delivered_at IS NOT NULL AND acked_at IS NULL', (int(ack), sensor_id)).fetchone()
        if row is not None:
            conn.execute('UPDATE commands SET acked_at = ? WHERE id = ?', (now, int(ack)))
        conn.execute('COMMIT')
    if row is None:
        return False
    db.record_event(path, 'success', 'Carte %s : ordre %d exécuté, %s.'
                    % (sensor_id, int(ack), describe(row['action'], row['value'])), sensor_id)
    return True
