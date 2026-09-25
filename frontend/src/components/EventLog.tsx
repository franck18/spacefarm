// Affiche et filtre les événements du journal.
import { useState } from 'react';
import { ListFilter, ArrowDown, CheckCheck, TriangleAlert, Circle } from 'lucide-react';
import { formatTime, type FarmEvent } from '../data/types';

export default function EventLog({ events }: { events: FarmEvent[] }) {
  const [warningsOnly, setWarningsOnly] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const filtered = events.filter(
    (e) => !/pompe|pump/i.test(e.message) && (!warningsOnly || e.kind === 'warning'),
  );
  const visible = expanded ? filtered : filtered.slice(0, 4);
  return (
    <section className="panel event-panel" id="journal" aria-labelledby="journal-title">
      <div className="panel-heading">
        <h2 id="journal-title">
          <ListFilter size={17} />
          Journal de bord
        </h2>
        <button
          className={`text-button filter-button ${warningsOnly ? 'amber' : ''}`}
          aria-pressed={warningsOnly}
          onClick={() => setWarningsOnly(!warningsOnly)}
        >
          {warningsOnly ? 'Tous les événements' : 'Alertes uniquement'}
        </button>
      </div>
      <div className="event-list">
        {visible.length ? (
          visible.map((e) => (
            <div className={`event-row ${e.kind}`} key={e.id}>
              <time dateTime={new Date(e.timestamp).toISOString()}>{formatTime(e.timestamp)}</time>
              {e.kind === 'warning' ? (
                <TriangleAlert size={13} />
              ) : e.kind === 'success' ? (
                <CheckCheck size={13} />
              ) : (
                <Circle size={7} />
              )}
              <span>{e.message}</span>
            </div>
          ))
        ) : (
          <div className="empty">
            <CheckCheck size={20} />
            <span>
              {warningsOnly
                ? 'Aucune alerte. Tout est sous contrôle.'
                : 'Aucun événement pour le moment.'}
            </span>
          </div>
        )}
      </div>
      {filtered.length > 4 && (
        <button className="text-button log-more" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Réduire le journal' : `Voir les ${filtered.length} événements`}
          <ArrowDown size={13} className={expanded ? 'rotated' : ''} />
        </button>
      )}
    </section>
  );
}
