"""Génère les alertes e-mail de SpaceFarm, sans stocker de mot de passe."""
import json
from pathlib import Path

# Seuils de démonstration, à adapter à la culture et à la calibration.
definitions = [
    ("water-low", "SpaceFarm · Réservoir faible", "5m",
     '.measurements.water.value as $v | if $v == null then 0 elif $v < 20 then 1 else 0 end',
     "Niveau d'eau estimé inférieur à 20 % depuis cinq minutes. Vérifier la sonde et le réservoir."),
    ("temperature", "SpaceFarm · Température anormale", "5m",
     '.measurements.temperature.value as $v | if $v == null then 0 elif $v < 18 or $v > 30 then 1 else 0 end',
     "Température hors de la plage 18–30 °C depuis cinq minutes."),
    ("sensor-missing", "SpaceFarm · Mesure indisponible", "2m",
     '[.measurements.temperature.value, .measurements.humidity.value, .measurements.light.value, .measurements.water.value] | if any(. == null) then 1 else 0 end',
     "Au moins une mesure est invalide ou périmée. Vérifier la Yún, les capteurs et leur connexion."),
]

rules = []
for name, title, duration, expression, message in definitions:
    # Une valeur 1 déclenche la règle ; 0 indique un fonctionnement normal.
    query = {
        "refId": "A", "type": "json", "source": "url", "parser": "jq-backend",
        "url": "http://127.0.0.1:8000/api/state", "url_options": {"method": "GET"},
        "root_selector": '[{value: (' + expression + ')}]', "format": "table",
        "columns": [{"selector": "value", "text": "value", "type": "number"}],
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "spacefarm-api"},
        "intervalMs": 60000, "maxDataPoints": 1,
    }
    condition = {
        "refId": "B", "type": "classic_conditions",
        "datasource": {"type": "__expr__", "uid": "__expr__"},
        "conditions": [{"type": "query", "query": {"params": ["A"]},
                        "reducer": {"type": "last", "params": []},
                        "evaluator": {"type": "gt", "params": [0.5]},
                        "operator": {"type": "and"}}],
    }
    rules.append({
        "uid": "spacefarm-" + name, "title": title, "condition": "B",
        "data": [
            {"refId": "A", "datasourceUid": "spacefarm-api",
             "relativeTimeRange": {"from": 600, "to": 0}, "model": query},
            {"refId": "B", "datasourceUid": "__expr__",
             "relativeTimeRange": {"from": 0, "to": 0}, "model": condition}],
        "for": duration, "noDataState": "Alerting", "execErrState": "Alerting",
        "isPaused": False, "labels": {"project": "spacefarm"},
        "notification_settings": {"receiver": "SpaceFarm e-mail",
                                  "group_by": ["grafana_folder", "alertname"],
                                  "group_wait": "30s", "group_interval": "5m",
                                  "repeat_interval": "4h"},
        "annotations": {"summary": message},
    })

output = {"apiVersion": 1, "groups": [{"orgId": 1, "name": "SpaceFarm",
          "folder": "SpaceFarm", "interval": "60s", "rules": rules}]}
output["contactPoints"] = [{"orgId": 1, "name": "SpaceFarm e-mail", "receivers": [{
    "uid": "spacefarm-email", "type": "email", "disableResolveMessage": False,
    "settings": {"addresses": "yusuke59160@gmail.com", "singleEmail": True}}]}]
Path(__file__).with_name("alerts.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
