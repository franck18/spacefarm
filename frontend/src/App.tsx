// Assemble les panneaux et calcule l’état global de la serre.
import { lazy, Suspense, useState } from 'react';
import {
  Sprout,
  FlaskConical,
  Info,
  CircleAlert,
  ArrowUpRight,
  X,
  WifiOff,
  ShieldAlert,
} from 'lucide-react';
import { useSpaceFarm } from './hooks/useSpaceFarm';
import { metricInfo, getMetricInfo, type Metric } from './data/types';
import MetricCards from './components/MetricCards';
import ControlPanel from './components/ControlPanel';
import CulturesPanel from './components/CulturesPanel';
import SystemPanel from './components/SystemPanel';
import WaterPanel from './components/WaterPanel';
import CrisisPanel from './components/CrisisPanel';
import EventLog from './components/EventLog';
import AssistantPanel from './components/AssistantPanel';
const HistoryPanel = lazy(() => import('./components/HistoryPanel'));

export default function App() {
  const farm = useSpaceFarm();
  const [metric, setMetric] = useState<Metric>('temperature');
  const [activeNav, setActiveNav] = useState('overview');
  const { data, disconnected } = farm;
  const water = data?.measurements.water.value;
  const critical = water !== null && water !== undefined && water < 15;
  const sensorError =
    data &&
    Object.values(data.measurements).some(
      (r) =>
        r.value === null ||
        r.quality !== 'ok' ||
        new Date(data.observedAt).getTime() - new Date(r.observedAt).getTime() > 10_000,
    );
  const outOfRange =
    data &&
    (Object.keys(metricInfo) as Metric[]).some((key) => {
      const v = data.measurements[key].value;
      const info = getMetricInfo(key, data);
      return v !== null && (v < info.min || v > info.max);
    });
  const warning = disconnected || sensorError || outOfRange;
  const status = critical ? 'CRITIQUE' : warning ? 'ATTENTION' : 'NORMAL';
  // Un seul message résume la priorité à traiter.
  let statusMessage = farm.isMock
    ? 'Conditions de démonstration favorables'
    : 'Conditions mesurées favorables';
  if (outOfRange) statusMessage = 'Conditions à surveiller';
  if (critical) statusMessage = 'Réserve d’eau critique';
  if (sensorError) statusMessage = 'Capteurs à brancher ou à vérifier';
  if (disconnected) statusMessage = 'Flux interrompu · dernières valeurs conservées';
  return (
    <>
      <a className="skip-link" href="#main">
        Aller au tableau de bord
      </a>
      <header className="site-header">
        <a
          className="brand"
          href="#overview"
          onClick={() => setActiveNav('overview')}
          aria-label="SpaceFarm 2080, accueil"
        >
          <Sprout size={32} strokeWidth={1.6} />
          <span>
            SPACEFARM<span className="brand-divider">/</span>
            <span className="brand-year">2080</span>
          </span>
        </a>
        <nav aria-label="Navigation principale">
          {[
            { id: 'overview', text: 'Vue d’ensemble' },
            { id: 'cultures', text: 'Cultures' },
            { id: 'journal', text: 'Journal' },
          ].map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={activeNav === item.id ? 'active' : ''}
              onClick={() => setActiveNav(item.id)}
            >
              {item.text}
            </a>
          ))}
        </nav>
        <div className="source-controls">
          <span className="source-badge">
            <FlaskConical size={14} />
            {farm.isMock ? 'Simulation' : 'Raspberry Pi'}
          </span>
          <a className="text-button" href={farm.isMock ? '?source=api' : '?source=mock'}>
            {farm.isMock ? 'Connecter au Pi' : 'Mode démo'}
          </a>
        </div>
      </header>
      <main id="main">
        <div id="overview" className="overview-heading">
          <div>
            <h1>
              Centre de contrôle<span className="heading-dot">.</span>
            </h1>
            <p>Un écosystème autonome. Une mission durable.</p>
          </div>
          <div className={`global-status ${critical ? 'red' : warning ? 'amber' : ''}`}>
            <span>
              <i className="dot" />
              {status}
            </span>
            <small>{statusMessage}</small>
          </div>
        </div>
        <div className="info-banner">
          <Info size={15} />
          <span>
            {farm.isMock ? 'Mode démonstration' : 'Source API'}
            <span className="banner-separator">—</span>
            {farm.isMock
              ? 'Données et équipements simulés. Aucun matériel piloté.'
              : 'État réel du Raspberry Pi. Mesures de culture indisponibles tant que les capteurs ne sont pas configurés.'}
          </span>
          <span className="refresh-label">Actualisation · 3 s</span>
        </div>
        {data?.scenario.active && (
          <div className="survival-banner" role="status">
            <ShieldAlert size={18} />
            <span>
              <strong>SURVIVAL MODE</strong> · 40 % de la réserve disponible. Les cultures sont
              priorisées.
            </span>
            <a href="#crise">
              Voir le scénario
              <ArrowUpRight size={14} />
            </a>
          </div>
        )}
        {disconnected && data && (
          <div className="offline-banner" role="alert">
            <WifiOff size={18} />
            <span>
              <strong>Données périmées.</strong> Les commandes sont désactivées.{' '}
              {farm.error ?? 'Rétablissez le flux dans « État du système ».'}
            </span>
          </div>
        )}
        {farm.actionError && (
          <div className="offline-banner" role="alert">
            <CircleAlert size={18} />
            <span>{farm.actionError}</span>
            <button
              className="icon-button"
              aria-label="Fermer le message"
              onClick={farm.dismissError}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {!data ? (
          <div className="loading-panel" role="status">
            <Sprout size={40} />
            <h2>
              {farm.error ? 'Connexion au service impossible' : 'Initialisation de SpaceFarm'}
            </h2>
            <p>{farm.error ?? 'Préparation des mesures…'}</p>
            {farm.error && (
              <p>
                Nouvelle tentative automatique toutes les 3 secondes. Aucun basculement vers des
                données simulées.
              </p>
            )}
          </div>
        ) : (
          <>
            <MetricCards data={data} stale={disconnected} selected={metric} onSelect={setMetric} />
            <div className="dashboard-grid">
              <Suspense
                fallback={
                  <section className="panel chart-loading">Chargement de l’historique…</section>
                }
              >
                <HistoryPanel data={data} metric={metric} setMetric={setMetric} />
              </Suspense>
              <ControlPanel data={data} disabled={disconnected || farm.pending} send={farm.send} />
              <CulturesPanel data={data} />
              <SystemPanel
                data={data}
                age={farm.age}
                disconnected={disconnected}
                paused={farm.paused}
                toggleConnection={farm.toggleConnection}
                reset={() => void farm.send({ type: 'reset' })}
                disabled={farm.pending}
              />
            </div>
            {!farm.isMock && <AssistantPanel />}
            <WaterPanel data={data} stale={disconnected} />
            <div className="bottom-grid">
              <EventLog events={data.events} />
              <div id="crise">
                <CrisisPanel
                  data={data}
                  disabled={disconnected || farm.pending}
                  toggle={() => void farm.send({ type: 'crisis', value: !data.scenario.active })}
                />
              </div>
            </div>
          </>
        )}
      </main>
      <footer>
        <span>
          <Sprout size={14} />
          SPACEFARM <span className="footer-divider">/</span> HORIZON 2080
        </span>
        <span>EPSI Bachelor 3 · FoodTech & AgriTech</span>
        <span>
          Prototype local
          <span className="dot" />
        </span>
      </footer>
    </>
  );
}
