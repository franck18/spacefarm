"""Décide sur le Pi si la LED de la serre doit être allumée."""
import commands
import db

YUN_SENSOR = 'spacefarm-yun'
# Le module A0 donne une grande valeur dans l'obscurité.
LIGHT_ON_RAW = 650
LIGHT_OFF_RAW = 450


def settings(path):
    """Lit le mode et la consigne manuelle conservés dans SQLite."""
    with db.session(path) as conn:
        rows = conn.execute("SELECT key, value FROM meta WHERE key IN ('lighting_mode', 'lighting_target')")
        values = {row['key']: row['value'] for row in rows}
    mode = values.get('lighting_mode', 'automatic')
    return (mode if mode in ('automatic', 'manual') else 'automatic',
            values.get('lighting_target', '0') == '1')


def set_mode(path, mode, current_lighting):
    """Passe en manuel sans changer l'état actuel de la LED."""
    if mode not in ('automatic', 'manual'):
        raise ValueError('Mode inconnu.')
    with db.session(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
                     ('lighting_mode', mode))
        if mode == 'manual':
            conn.execute('INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
                         ('lighting_target', '1' if current_lighting else '0'))
        conn.execute('COMMIT')


def set_manual_target(path, enabled):
    """Mémorise l'ordre voulu par le bouton du tableau de bord."""
    with db.session(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute("SELECT value FROM meta WHERE key = 'lighting_mode'").fetchone()
        if row is None or row['value'] != 'manual':
            conn.execute('ROLLBACK')
            raise ValueError('Passez en mode manuel avant de commander la LED.')
        conn.execute('INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)',
                     ('lighting_target', '1' if enabled else '0'))
        conn.execute('COMMIT')


def reconcile(path, sensor_id, readings):
    """Compare la consigne du Pi à l'état renvoyé par la Yún."""
    if sensor_id != YUN_SENSOR:
        return None
    values = {item['metric']: item['value'] for item in readings
              if item['quality'] == 'ok'}
    current = values.get('lighting')
    if current not in (0, 1):
        return None
    mode, manual_target = settings(path)
    if mode == 'manual':
        desired = int(manual_target)
    else:
        raw = values.get('light_raw')
        if raw is None:
            return None
        # Entre les deux seuils, garder l'état pour éviter le clignotement.
        desired = current
        if raw >= LIGHT_ON_RAW:
            desired = 1
        elif raw <= LIGHT_OFF_RAW:
            desired = 0
    if current == desired:
        return None
    return commands.queue(path, sensor_id, 'lighting', desired)
