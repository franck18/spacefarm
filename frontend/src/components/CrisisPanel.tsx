// Présente la simulation de pénurie, isolée du matériel.
import { ShieldAlert, ArrowUpRight, Check, Info } from 'lucide-react';
import { waterPlan } from '../data/engine';
import { formatNumber, type Snapshot } from '../data/types';

export default function CrisisPanel({
  data,
  disabled,
  toggle,
}: {
  data: Snapshot;
  disabled: boolean;
  toggle: () => void;
}) {
  const plan = waterPlan(data);
  const active = data.scenario.active;
  return (
    <section
      className={`panel crisis-panel ${active ? 'crisis-active' : ''}`}
      aria-labelledby="crisis-title"
    >
      <div className="crisis-heading">
        <span className="crisis-icon">
          <ShieldAlert size={22} />
        </span>
        <div>
          <h2 id="crisis-title">{active ? 'Survival Mode activé' : 'Préparer l’imprévu'}</h2>
          <p>
            {active
              ? '40 % de la réserve de référence disponible.'
              : 'Et si seulement 40 % de l’eau restait disponible ?'}
          </p>
        </div>
        <span className="scenario-tag">SCÉNARIO</span>
      </div>
      {active && (
        <div className="crisis-result" role="status">
          <div>
            <span>Budget pour 48 h</span>
            <strong>{plan.available === null ? '—' : formatNumber(plan.available, 2)} L</strong>
          </div>
          <div>
            <span>Allocation prévue</span>
            <strong>{formatNumber(plan.required, 2)} L</strong>
          </div>
          <span className={plan.meetsTarget ? 'target-ok' : 'amber'}>
            {plan.meetsTarget ? <Check size={15} /> : <Info size={15} />}
            {plan.meetsTarget ? 'Objectif 48 h atteint*' : 'Objectif 48 h non atteint'}
          </span>
        </div>
      )}
      <div className="crisis-bottom">
        {data.source === 'live' ? (
          <a className="crisis-button" href="?source=mock">
            Ouvrir la démonstration
            <ArrowUpRight size={15} />
          </a>
        ) : (
          <button className="crisis-button" disabled={disabled} onClick={toggle}>
            {active ? 'Terminer la simulation' : 'Simuler une crise'}
            <ArrowUpRight size={15} />
          </button>
        )}
        <p>
          {data.source === 'live'
            ? 'Scénario isolé des données et équipements réels.'
            : active
              ? '*Selon les besoins théoriques du scénario.'
              : 'Priorités réorganisées. Aucun effet sur le matériel.'}
        </p>
      </div>
    </section>
  );
}
