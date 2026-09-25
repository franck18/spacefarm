// Affiche le mode et le bouton de commande de la LED.
import { Info, Settings2, Sun } from 'lucide-react';
import type { Command, Snapshot } from '../data/types';

export default function ControlPanel({
  data,
  disabled,
  send,
}: {
  data: Snapshot;
  disabled: boolean;
  send: (c: Command) => void;
}) {
  const manual = data.mode === 'manual';
  const unavailable = !data.system.controlsAvailable;
  const blocked = disabled || unavailable;
  const live = data.source === 'live';
  let description = data.lighting
    ? 'Éclairage des cultures actif'
    : 'Éclairage des cultures arrêté';
  if (live) description = 'LED pilotée par le Raspberry Pi';
  if (unavailable) description = 'Équipement indisponible';

  // Expliquer pourquoi un bouton est disponible ou bloqué.
  let note = 'Éclairage automatique simulé. Passez en manuel pour intervenir.';
  if (live) note = 'Le Raspberry Pi allume la LED dans l’obscurité et l’éteint à la lumière.';
  if (manual)
    note = live
      ? 'Le bouton Éclairage commande la LED via le Raspberry Pi.'
      : 'Éclairage simulé. Aucun matériel piloté.';
  if (blocked) note = 'Commandes indisponibles pendant la coupure ou l’envoi.';
  if (unavailable) note = 'Commande indisponible : attendez un état récent de la Yún.';
  return (
    <section className="panel control-panel" aria-labelledby="control-title">
      <div className="panel-heading">
        <h2 id="control-title">
          <Settings2 size={17} />
          Automatisation
        </h2>
        <span className="tiny-label">{data.source === 'mock' ? 'SIMULÉE' : 'COMMANDE'}</span>
      </div>
      <div className="mode-switch" role="group" aria-label="Mode de fonctionnement">
        <button
          disabled={blocked}
          aria-pressed={data.mode === 'automatic'}
          className={data.mode === 'automatic' ? 'active' : ''}
          onClick={() => send({ type: 'mode', value: 'automatic' })}
        >
          Automatique
        </button>
        <button
          disabled={blocked}
          aria-pressed={manual}
          className={manual ? 'active' : ''}
          onClick={() => send({ type: 'mode', value: 'manual' })}
        >
          Manuel
        </button>
      </div>
      <div className={`actuator ${data.lighting ? 'on' : ''}`}>
        <span className="actuator-icon">
          <Sun size={21} />
        </span>
        <div>
          <h3>Éclairage</h3>
          <p>{description}</p>
        </div>
        <div className="switch-container">
          <button
            type="button"
            role="switch"
            aria-checked={data.lighting ?? false}
            aria-label="Éclairage"
            disabled={blocked || !manual}
            className="toggle"
            onClick={() => send({ type: 'lighting', value: !data.lighting })}
          >
            <span />
          </button>
          <span className="switch-label">
            {data.lighting === null ? '—' : data.lighting ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>
      <p className="panel-note">
        <Info size={14} />
        <span>{note}</span>
      </p>
      {data.source === 'live' && !unavailable && (
        <p className="caption">
          Retour :{' '}
          {data.actuatorFeedback === 'measured'
            ? 'état mesuré'
            : 'commande appliquée, fonctionnement physique non confirmé'}
          .
        </p>
      )}
    </section>
  );
}
