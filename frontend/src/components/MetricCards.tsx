// Affiche les quatre mesures principales et leur état.
import { Droplets, Sun, Thermometer, Cylinder, ArrowUpRight } from 'lucide-react';
import { formatNumber, metricInfo, getMetricInfo, type Metric, type Snapshot } from '../data/types';

const icons = { temperature: Thermometer, humidity: Droplets, light: Sun, water: Cylinder };

export default function MetricCards({
  data,
  stale,
  selected,
  onSelect,
}: {
  data: Snapshot;
  stale: boolean;
  selected: Metric;
  onSelect: (m: Metric) => void;
}) {
  return (
    <section className="metrics" aria-label="Mesures de la ferme">
      {(Object.keys(metricInfo) as Metric[]).map((key) => {
        const info = getMetricInfo(key, data);
        const reading = data.measurements[key];
        const Icon = icons[key];
        const valid = reading.value !== null && reading.quality === 'ok';
        const warning = valid && (reading.value! < info.min || reading.value! > info.max);
        const points = data.history
          .slice(-30)
          .map((p) => p[key])
          .filter((n): n is number => n !== null);
        const min = Math.min(...points),
          max = Math.max(...points);
        const line = points
          .map(
            (p, i) =>
              `${(i / Math.max(1, points.length - 1)) * 120},${32 - ((p - min) / Math.max(max - min, 0.1)) * 25}`,
          )
          .join(' ');
        const label = stale
          ? 'Données périmées'
          : !valid
            ? 'Mesure indisponible'
            : warning
              ? 'À surveiller'
              : key === 'water'
                ? 'Réserve suffisante'
                : key === 'light' && info.unit === '%'
                  ? 'Indice relatif mesuré'
                  : key === 'light'
                    ? data.lighting
                      ? 'Éclairage actif'
                      : 'Éclairage éteint'
                    : 'Dans la plage cible';
        return (
          <button
            type="button"
            className={`metric-card ${selected === key ? 'selected' : ''}`}
            key={key}
            onClick={() => onSelect(key)}
            aria-pressed={selected === key}
            aria-label={`Afficher l’historique : ${info.label}`}
          >
            <div className="metric-top">
              <span>
                <Icon size={17} />
                {info.label}
              </span>
              <ArrowUpRight size={14} className="metric-arrow" />
            </div>
            <div className="metric-value">
              {!valid || stale ? '—' : formatNumber(reading.value!, info.decimals)}
              <span>{info.unit}</span>
            </div>
            {key === 'light' && info.unit === '%' && (
              <small>Référence provisoire · pas des lux</small>
            )}
            <div className="metric-bottom">
              <span className={`metric-condition ${stale || !valid || warning ? 'amber' : ''}`}>
                <i className="dot" />
                {label}
              </span>
              <svg className="sparkline" viewBox="0 0 120 38" aria-hidden="true">
                <polyline points={line} />
              </svg>
            </div>
          </button>
        );
      })}
    </section>
  );
}
