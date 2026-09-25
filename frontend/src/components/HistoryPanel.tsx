// Trace la mesure choisie sur la période sélectionnée.
import { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartNoAxesCombined } from 'lucide-react';
import {
  formatNumber,
  formatTime,
  metricInfo,
  getMetricInfo,
  type Metric,
  type Snapshot,
} from '../data/types';

export default function HistoryPanel({
  data,
  metric,
  setMetric,
}: {
  data: Snapshot;
  metric: Metric;
  setMetric: (m: Metric) => void;
}) {
  const [hours, setHours] = useState(1);
  const info = getMetricInfo(metric, data);
  const end = new Date(data.observedAt).getTime();
  const points = data.history.filter((p) => p.timestamp >= end - hours * 3_600_000);
  const values = points.map((p) => p[metric]).filter((v): v is number => v !== null);
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;
  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  const metricText = (n: number | null) =>
    n === null ? '—' : `${formatNumber(n, info.decimals)} ${info.unit}`;
  return (
    <section className="panel history-panel" id="historique" aria-labelledby="history-title">
      <div className="panel-heading">
        <h2 id="history-title">
          <ChartNoAxesCombined size={17} />
          Évolution des mesures
        </h2>
        <span className="caption">
          {data.source === 'mock' ? 'Historique simulé' : 'Historique des mesures'}
        </span>
      </div>
      <div className="chart-toolbar">
        <div className="metric-tabs" role="group" aria-label="Mesure du graphique">
          {(Object.keys(metricInfo) as Metric[]).map((key) => (
            <button
              key={key}
              className={metric === key ? 'active' : ''}
              aria-pressed={metric === key}
              onClick={() => setMetric(key)}
            >
              {key === 'humidity' ? 'Humidité' : getMetricInfo(key, data).label}
            </button>
          ))}
        </div>
        <div className="period-tabs" role="group" aria-label="Période du graphique">
          {[1, 6, 24].map((h) => (
            <button
              key={h}
              className={hours === h ? 'active' : ''}
              aria-pressed={hours === h}
              onClick={() => setHours(h)}
            >
              {h} h
            </button>
          ))}
        </div>
      </div>
      <div
        className="chart-area"
        role="img"
        aria-label={`${info.label} sur ${hours} heures. Minimum ${metricText(min)}, maximum ${metricText(max)}, moyenne ${metricText(avg)}.`}
      >
        {values.length ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <AreaChart data={points} margin={{ top: 16, right: 6, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#aeeec8" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#aeeec8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#2b3430" strokeDasharray="3 5" vertical={false} />
              <XAxis
                dataKey="timestamp"
                type="number"
                domain={[end - hours * 3_600_000, end]}
                tickFormatter={(v) => formatTime(v)}
                tick={{ fill: '#8f9b94', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                domain={info.domain}
                tick={{ fill: '#8f9b94', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickCount={5}
              />
              <Tooltip
                labelFormatter={(v) => formatTime(Number(v))}
                formatter={(v) => [metricText(Number(v)), info.label]}
                contentStyle={{
                  background: '#202924',
                  border: '1px solid #415348',
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#edf5ee',
                }}
                itemStyle={{ color: '#b5f4ce' }}
              />
              <Area
                type="monotone"
                dataKey={metric}
                stroke="#b5f4ce"
                strokeWidth={2}
                fill="url(#chart-fill)"
                isAnimationActive={false}
                connectNulls={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty">Aucune mesure disponible sur cette période.</div>
        )}
      </div>
      <div className="chart-summary">
        <span>
          MIN <strong>{metricText(min)}</strong>
        </span>
        <span>
          MOYENNE <strong>{metricText(avg)}</strong>
        </span>
        <span>
          MAX <strong>{metricText(max)}</strong>
        </span>
        <span className="chart-unit">
          {info.unit} · {hours} dernière{hours > 1 ? 's' : ''} heure{hours > 1 ? 's' : ''}
        </span>
      </div>
    </section>
  );
}
