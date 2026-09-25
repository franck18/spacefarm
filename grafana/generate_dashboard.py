"""Crée le dashboard Grafana à partir de l'API existante, sans dupliquer les calculs."""
import json
from pathlib import Path

SOURCE = {"type": "yesoreyeram-infinity-datasource", "uid": "spacefarm-api"}
panels = []


def query(selector, columns, history=False):
    """Une lecture HTTP ; JQ sélectionne les champs à afficher."""
    return {
        "refId": "A", "datasource": SOURCE, "type": "json", "source": "url",
        "url": "http://127.0.0.1:8000/api/state", "url_options": {"method": "GET"},
        "parser": "jq-backend", "root_selector": selector,
        "format": "timeseries" if history else "table",
        "columns": [{"selector": key, "text": label, "type": kind}
                    for key, label, kind in columns],
    }


def panel(title, kind, position, target, unit="none", maximum=None):
    defaults = {"unit": unit, "decimals": 1, "noValue": "Indisponible",
                "color": {"mode": "palette-classic"}}
    if maximum is not None:
        defaults.update(min=0, max=maximum)
    result = {"id": len(panels) + 1, "title": title, "type": kind,
              "gridPos": dict(zip(("x", "y", "w", "h"), position)),
              "datasource": SOURCE, "targets": [target],
              "fieldConfig": {"defaults": defaults, "overrides": []},
              "options": {"reduceOptions": {"calcs": ["last"], "fields": "", "values": False},
                          "colorMode": "value", "graphMode": "none"}}
    panels.append(result)
    return result


# L'API fournit déjà les pourcentages et masque les mesures périmées.
metrics = [("temperature", "Température", "celsius", None),
           ("humidity", "Humidité de l'air", "percent", 100),
           ("light", "Luminosité relative", "percent", 100),
           ("water", "Niveau d'eau estimé", "percent", 100)]
for index, (key, title, unit, maximum) in enumerate(metrics):
    item = panel(title, "stat", (index * 6, 0, 6, 5),
                 query('[{value: .measurements.' + key + '.value}]',
                       [("value", title, "number")]), unit, maximum)
    item["description"] = "Valeur actuelle. Indisponible si invalide ou sans mesure depuis 120 secondes."
    if key == "light":
        item["description"] += " Pourcentage relatif étalonné, pas une mesure en lux."
    if key == "water":
        item["description"] += " Estimation de la sonde ; calibration à vérifier après son déplacement."

for index, (key, title, unit, maximum) in enumerate(metrics):
    item = panel(title + " — historique", "timeseries", ((index % 2) * 12, 9 + (index // 2) * 8, 12, 8),
                 query('.history', [("timestamp", "Heure", "timestamp_epoch"),
                                    (key, title, "number")], True), unit, maximum)
    item["description"] = "Historique fourni par l'API : six dernières heures."
    item["fieldConfig"]["defaults"]["custom"] = {"drawStyle": "line", "lineWidth": 2,
        "fillOpacity": 12, "spanNulls": False, "showPoints": "never", "axisLabel": ""}
    item["options"] = {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                       "tooltip": {"mode": "single", "sort": "none"}}

led = panel("Éclairage · état confirmé", "stat", (0, 5, 6, 4),
            query('[{value: (if .lighting == null then null elif .lighting then 1 else 0 end)}]',
                  [("value", "LED", "number")]))
led["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {
    "0": {"text": "Éteint", "color": "gray"}, "1": {"text": "Allumé", "color": "green"}}}]
mode = panel("Automatisation", "stat", (6, 5, 6, 4),
             query('[{value: .mode}]', [("value", "Mode", "string")]))
mode["options"]["reduceOptions"]["fields"] = "/.*/"
mode["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {
    "automatic": {"text": "Automatique", "color": "green"},
    "manual": {"text": "Manuel", "color": "blue"},
    "unconfigured": {"text": "Capteurs hors ligne", "color": "orange"}}}]
panel("Raspberry Pi · température CPU", "stat", (12, 5, 6, 4),
      query('[{value: .system.cpuTemperature}]', [("value", "CPU", "number")]), "celsius")
panel("Raspberry Pi · mémoire utilisée", "stat", (18, 5, 6, 4),
      query('[{value: .system.memoryUsedPercent}]', [("value", "RAM", "number")]), "percent", 100)

# Une mesure absente doit être visible comme un avertissement.
for item in panels:
    item["fieldConfig"]["defaults"].setdefault("mappings", []).append({
        "type": "special", "options": {"match": "null", "result": {
            "text": "Indisponible", "color": "orange"}}})

dashboard = {
    "uid": "spacefarm-2080", "title": "SpaceFarm 2080 · Capteurs", "schemaVersion": 39,
    "version": 1, "tags": ["SpaceFarm", "FoodTech"], "editable": False,
    "timezone": "browser", "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
    "description": "Mesures de l'API SpaceFarm. Historique des six dernières heures ; commandes sur le centre de contrôle.",
    "links": [{"title": "Centre de contrôle · commander la LED", "type": "link",
               "url": "http://192.168.41.88:8000/?source=api", "targetBlank": True}],
    "timepicker": {"refresh_intervals": ["15s", "30s", "1m", "5m"]}, "panels": panels,
}
Path(__file__).with_name("spacefarm.json").write_text(
    json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
