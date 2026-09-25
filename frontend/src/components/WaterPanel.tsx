// Affiche le niveau d’eau en % et les estimations disponibles.
import { Droplets, Info } from 'lucide-react';
import { waterPlan } from '../data/engine';
import { formatNumber, type Snapshot } from '../data/types';

export default function WaterPanel({ data, stale = false }: { data: Snapshot; stale?: boolean }) {
  const plan = waterPlan(data);
  const known = data.reservoirLiters !== null;
  const smallReservoir = data.reservoirCapacity !== null && data.reservoirCapacity < 1;
  // Le débit du petit réservoir réel n’est pas encore mesuré.
  const hideEstimates = smallReservoir && data.source === 'live';
  const autonomy = hideEstimates || plan.autonomy === null ? '—' : formatNumber(plan.autonomy);
  const water = data.measurements.water;
  const levelKnown = !stale && water.quality === 'ok' && water.value !== null;
  return (
    <section className="water-strip" aria-label="Autonomie en eau estimée">
      <div className="water-strip-title">
        <Droplets size={19} />
        <span>
          Chaque goutte compte
          <small>
            {data.scenario.active ? 'Budget du scénario de crise' : 'Gestion de la réserve'}
          </small>
        </span>
      </div>
      <div>
        <span className="caption">Niveau du réservoir</span>
        <strong>
          {levelKnown ? formatNumber(water.value!) : '—'} <small>%</small>
        </strong>
      </div>
      <div>
        <span className="caption">Besoins théoriques</span>
        <strong>
          {hideEstimates ? '—' : formatNumber(plan.daily, 2)}{' '}
          <small>{hideEstimates ? 'non mesurés' : 'L / jour'}</small>
        </strong>
      </div>
      <div>
        <span className="caption">Autonomie estimée</span>
        <strong className={data.scenario.active ? 'amber' : 'mint'}>
          {autonomy}{' '}
          <small>{hideEstimates ? 'débit à mesurer' : known ? 'heures' : 'inconnue'}</small>
        </strong>
      </div>
      <span className="water-estimate">
        <Info size={14} />
        <span>
          {levelKnown ? (
            data.source === 'mock' ? (
              <>
                Niveau simulé
                <br />
                démonstration
              </>
            ) : (
              <>
                Niveau estimé
                <br />
                étalonnage prototype
              </>
            )
          ) : (
            <>
              Niveau d’eau
              <br />
              indisponible
            </>
          )}
        </span>
      </span>
    </section>
  );
}
