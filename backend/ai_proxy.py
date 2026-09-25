"""Relais local vers Codex sur le PC, via le tunnel SSH."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def forward(action, payload, access_code):
    if action not in ('status', 'login', 'logout', 'ask'):
        return 404, {'error': 'Action inconnue.'}
    if not access_code or len(access_code) > 128:
        return 401, {'error': 'Saisis le code d’accès de l’assistant.'}
    request = Request('http://127.0.0.1:8765/' + action,
                      data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'X-SpaceFarm-Code': access_code})
    try:
        with urlopen(request, timeout=110) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)
    except (URLError, TimeoutError, OSError):
        return 503, {'error': 'Assistant indisponible. Vérifie le PC et le tunnel SSH.'}
