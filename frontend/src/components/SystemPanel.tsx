// Affiche la connexion, les capteurs et les informations du Pi.
import { useState } from 'react';
import { Cpu, Radio, Clock3, ChevronDown, Unplug, PlugZap, RotateCcw } from 'lucide-react';
import { formatNumber, formatTime, metricInfo, type Snapshot } from '../data/types';

export default function SystemPanel({
  data,
  age,
  disconnected,
  paused,
  toggleConnection,
  reset,
  disabled,
}: {
  data: Snapshot;
  age: number;
  disconnected: boolean;
  paused: boolean;
  toggleConnection: () => void;
  reset: () => void;
  disabled: boolean;
}) {
  const [details, setDetails] = useState(false);
  const good = Object.values(data.measurements).filter(
    (r) => r.quality === 'ok' && r.value !== null,
  ).length;
  return (
    <section className="panel system-panel" aria-labelledby="system-title">
      <div className="panel-heading">
        <h2 id="system-title">
          <Cpu size={17} />
          État du système
        </h2>
        <span
          className={`connection-dot ${disconnected ? 'offline' : ''}`}
          aria-label={disconnected ? 'Connexion interrompue' : 'Flux actif'}
        />
      </div>
      <div className="system-row">
        <Cpu size={16} />
        <span>Raspberry Pi 3</span>
        <strong>
          {data.source === 'mock'
            ? 'Non connecté · démo'
            : disconnected
              ? 'Injoignable'
              : 'API connectée'}
        </strong>
      </div>
      <button
        className="system-row sensor-details"
        onClick={() => setDetails(!details)}
        aria-expanded={details}
      >
        <Radio size={16} />
        <span>Capteurs</span>
        <strong>
          {good} / 4 {data.source === 'mock' ? 'simulés' : 'disponibles'}
          <ChevronDown size={14} className={details ? 'rotated' : ''} />
        </strong>
      </button>
      {details && (
        <ul className="sensors-list">
          {Object.entries(data.measurements).map(([key, r]) => (
            <li key={key}>
              <span>{metricInfo[key as keyof typeof metricInfo].label}</span>
              <span>
                {disconnected
                  ? 'Périmé'
                  : r.quality === 'ok' && r.value !== null
                    ? 'OK'
                    : 'Indisponible'}{' '}
                · {formatTime(r.observedAt)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="system-row">
        <Clock3 size={16} />
        <span>Dernière réponse</span>
        <strong className={disconnected ? 'amber' : ''}>
          {age < 2 ? 'À l’instant' : `Il y a ${age} s`}
        </strong>
      </div>
      {data.source === 'live' && (
        <>
          <div className="system-row">
            <Cpu size={16} />
            <span>Température CPU</span>
            <strong>
              {data.system.cpuTemperature === null
                ? '—'
                : `${formatNumber(data.system.cpuTemperature, 1)} °C`}
            </strong>
          </div>
          <div className="system-row">
            <Clock3 size={16} />
            <span>Pi en fonctionnement</span>
            <strong>
              {data.system.uptimeSeconds === null
                ? '—'
                : `${Math.floor(data.system.uptimeSeconds / 3600)} h ${Math.floor((data.system.uptimeSeconds % 3600) / 60)} min`}
            </strong>
          </div>
          <p className="caption" style={{ marginTop: 12 }}>
            {data.system.hostname} · {data.system.os}
            <br />
            Mémoire utilisée :{' '}
            {data.system.memoryUsedPercent === null
              ? '—'
              : `${formatNumber(data.system.memoryUsedPercent)} %`}
          </p>
          {Math.abs(Date.now() - new Date(data.observedAt).getTime()) > 60_000 && (
            <p className="caption amber" style={{ marginTop: 8 }}>
              Horloge du Pi décalée. Les heures du journal sont celles du Pi.
            </p>
          )}
        </>
      )}
      {data.source === 'mock' && (
        <div className="demo-tools">
          <button className="text-button" onClick={toggleConnection}>
            {paused ? <PlugZap size={13} /> : <Unplug size={13} />}
            {paused ? 'Rétablir le flux' : 'Tester une coupure'}
          </button>
          <button
            className="icon-button"
            title="Réinitialiser la démonstration"
            aria-label="Réinitialiser la démonstration"
            disabled={disabled || disconnected}
            onClick={reset}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      )}
    </section>
  );
}
