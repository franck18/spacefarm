// Présente les profils et les allocations théoriques des cultures.
import { Sprout, Leaf, FlaskConical, Pause } from 'lucide-react';
import { crops } from '../data/engine';
import { formatNumber, type Snapshot } from '../data/types';

export default function CulturesPanel({ data }: { data: Snapshot }) {
  const crisis = data.scenario.active;
  return (
    <section className="panel cultures-panel" id="cultures" aria-labelledby="cultures-title">
      <div className="panel-heading">
        <h2 id="cultures-title">
          <Sprout size={18} />
          Les cultures
        </h2>
        <span className="caption">3 profils de culture théoriques</span>
      </div>
      <div className="crop-table" role="table" aria-label="Priorités des cultures simulées">
        <div className="crop-row table-head" role="row">
          <span role="columnheader">Culture</span>
          <span role="columnheader">Priorité</span>
          <span role="columnheader">Allocation / 24 h</span>
          <span role="columnheader">Irrigation</span>
        </div>
        {crops.map((crop, i) => {
          const Icon = i === 0 ? Sprout : i === 1 ? Leaf : FlaskConical;
          const allocation = crisis ? crop.survivalLiters : crop.dailyLiters;
          return (
            <div
              className={`crop-row ${crisis && i === 2 ? 'suspended' : ''}`}
              role="row"
              key={crop.name}
            >
              <div role="cell" className="crop-name">
                <span className="crop-icon">
                  <Icon size={19} />
                </span>
                <span>
                  <strong>{crop.name}</strong>
                  <small>{crop.role}</small>
                </span>
              </div>
              <span role="cell">
                <span className={`priority p${i}`}>{crop.priority}</span>
              </span>
              <span role="cell" className="allocation">
                {formatNumber(allocation, 2)} <small>L</small>
              </span>
              <span role="cell" className={`irrigation ${crisis && i === 2 ? 'amber' : ''}`}>
                {crisis && i === 2 ? <Pause size={12} /> : <i className="dot" />}
                {crisis
                  ? i === 2
                    ? 'Suspendue'
                    : i === 1
                      ? 'Réduite'
                      : 'Prioritaire'
                  : data.source === 'live'
                    ? 'Non équipée'
                    : 'Planifiée'}
              </span>
            </div>
          );
        })}
      </div>
      <p className="caption crop-footnote">
        Allocations théoriques pour la démonstration · à calibrer selon les cultures réelles.
      </p>
    </section>
  );
}
