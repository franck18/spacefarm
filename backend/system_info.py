"""Lit les informations du Raspberry dans les fichiers Linux."""
from pathlib import Path
import socket


def read_text(path):
    """Renvoie un texte vide si le fichier est inaccessible."""
    try:
        return Path(path).read_text().strip().replace('\x00', '')
    except (OSError, UnicodeError):
        return ''


def system_info():
    """Renvoie température CPU, mémoire et durée de fonctionnement."""
    try:
        uptime = float(read_text('/proc/uptime').split()[0])
    except (ValueError, IndexError):
        uptime = None
    try:
        temperature = round(float(read_text('/sys/class/thermal/thermal_zone0/temp')) / 1000, 1)
    except ValueError:
        temperature = None
    try:
        memory = {line.split(':')[0]: int(line.split()[1]) for line in read_text('/proc/meminfo').splitlines()}
        memory_percent = round((1 - memory['MemAvailable'] / memory['MemTotal']) * 100, 1)
    except (KeyError, ValueError, ZeroDivisionError, IndexError):
        memory_percent = None
    os_name = next((line.split('=', 1)[1].strip('"') for line in read_text('/etc/os-release').splitlines()
                    if line.startswith('PRETTY_NAME=')), 'Linux')
    return {
        'hostname': socket.gethostname(),
        'model': read_text('/proc/device-tree/model') or 'Matériel non identifié',
        'os': os_name, 'uptimeSeconds': uptime, 'cpuTemperature': temperature,
        'memoryUsedPercent': memory_percent, 'controlsAvailable': False,
    }
