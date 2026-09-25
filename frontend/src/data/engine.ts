// Calcule uniquement les données et les scénarios de démonstration.
import type { Command, Snapshot } from './types';

export const crops = [
  {
    name: 'Laitue romaine',
    role: 'Culture principale',
    priority: 'Élevée',
    dailyLiters: 1.2,
    survivalLiters: 1.05,
  },
  {
    name: 'Basilic',
    role: 'Culture secondaire',
    priority: 'Moyenne',
    dailyLiters: 0.72,
    survivalLiters: 0.45,
  },
  {
    name: 'Tomate',
    role: 'Culture expérimentale',
    priority: 'Faible',
    dailyLiters: 0.48,
    survivalLiters: 0,
  },
] as const;

export function waterPlan(s: Snapshot) {
  const available = s.scenario.active
    ? s.scenario.referenceLiters === null
      ? null
      : s.scenario.referenceLiters * s.scenario.fraction
    : s.reservoirLiters;
  const daily = crops.reduce(
    (sum, c) => sum + (s.scenario.active ? c.survivalLiters : c.dailyLiters),
    0,
  );
  const required = daily * 2;
  return {
    available,
    daily,
    required,
    autonomy: available === null ? null : (available / daily) * 24,
    meetsTarget: available !== null && available >= required,
  };
}

export function createSnapshot(now = Date.now()): Snapshot {
  const history = Array.from({ length: 289 }, (_, i) => ({
    timestamp: now - (288 - i) * 300_000,
    temperature: 23.5 + Math.sin(i * 0.15) * 0.45 + Math.sin(i * 0.8) * 0.18,
    humidity: 62 + Math.sin(i * 0.12) * 3,
    light: 58 + Math.sin(i * 0.22) * 2.8,
    water: 76 + ((288 - i) / 288) * 24,
  }));
  history[288] = { timestamp: now, temperature: 23.8, humidity: 62, light: 58, water: 76 };
  const reading = (value: number) => ({
    value,
    quality: 'ok' as const,
    observedAt: new Date(now).toISOString(),
  });
  return {
    schemaVersion: 1,
    source: 'mock',
    observedAt: new Date(now).toISOString(),
    mode: 'automatic',
    measurements: {
      temperature: reading(23.8),
      humidity: reading(62),
      light: { ...reading(58), unit: '%' },
      water: reading(76),
    },
    pump: false,
    lighting: true,
    actuatorFeedback: 'simulated',
    reservoirLiters: 7.6,
    reservoirCapacity: 10,
    scenario: { active: false, referenceLiters: 7.6, fraction: 1 },
    history,
    system: {
      hostname: 'raspberrypi',
      model: 'Raspberry Pi 3',
      os: 'Simulation',
      uptimeSeconds: null,
      cpuTemperature: null,
      memoryUsedPercent: null,
      controlsAvailable: true,
    },
    events: [
      {
        id: 'start',
        timestamp: now,
        kind: 'info',
        message: 'Démonstration démarrée · historique initial synthétique',
      },
    ],
  };
}

function addEvent(
  s: Snapshot,
  message: string,
  kind: Snapshot['events'][number]['kind'],
  now: number,
) {
  s.events = [
    { id: `${now}-${s.events.length}-${message}`, timestamp: now, kind, message },
    ...s.events,
  ].slice(0, 100);
}

export function applyCommand(current: Snapshot, command: Command, now = Date.now()): Snapshot {
  if (current.source !== 'mock')
    throw new Error('Le simulateur ne peut pas commander du matériel réel.');
  if (command.type === 'reset') return createSnapshot(now);
  const s = structuredClone(current);
  if (command.type === 'mode') {
    s.mode = command.value;
    // Arrêter un cycle manuel lors du changement de mode.
    s.pump = false;
    if (command.value === 'automatic') s.lighting = true;
    addEvent(
      s,
      `Mode ${s.mode === 'automatic' ? 'automatique' : 'manuel'} activé · pompe arrêtée`,
      'info',
      now,
    );
  } else if (command.type === 'crisis') {
    s.scenario = {
      active: command.value,
      referenceLiters: s.reservoirLiters,
      fraction: command.value ? 0.4 : 1,
    };
    addEvent(
      s,
      command.value
        ? 'Survival Mode · budget d’eau réduit à 40 %'
        : 'Simulation de crise terminée · priorités rétablies',
      command.value ? 'warning' : 'success',
      now,
    );
  } else {
    if (s.mode !== 'manual')
      throw new Error('Passez en mode manuel pour commander les équipements.');
    if (
      command.type === 'pump' &&
      command.value &&
      (s.measurements.water.value === null ||
        s.measurements.water.quality !== 'ok' ||
        s.measurements.water.value < 15)
    ) {
      throw new Error('Pompe bloquée : niveau d’eau insuffisant ou inconnu.');
    }
    s[command.type] = command.value;
    addEvent(
      s,
      `${command.type === 'pump' ? 'Pompe' : 'Éclairage'} ${command.value ? 'activé' : 'désactivé'} · commande simulée`,
      'info',
      now,
    );
  }
  return s;
}

export function advanceSnapshot(current: Snapshot, now: number, startedAt: number): Snapshot {
  const s = structuredClone(current);
  if (s.source !== 'mock' || s.reservoirLiters === null || s.reservoirCapacity === null)
    throw new Error('Données de simulation requises.');
  const previousTime = new Date(current.observedAt).getTime();
  const elapsed = Math.max(0, (now - previousTime) / 3_600_000);
  const seconds = (now - startedAt) / 1000;
  const previousWater = current.measurements.water.value;
  s.reservoirLiters = Math.max(0, s.reservoirLiters - elapsed * 0.1);
  s.observedAt = new Date(now).toISOString();
  const values = {
    temperature: 23.8 + Math.sin(seconds / 65) * 0.4,
    humidity: 62 + Math.sin(seconds / 80) * 2,
    light: s.lighting ? 58 + Math.sin(seconds / 40) * 2 : 2.4,
    water: (s.reservoirLiters / s.reservoirCapacity) * 100,
  };
  for (const key of Object.keys(values) as (keyof typeof values)[]) {
    s.measurements[key] = { value: values[key], quality: 'ok', observedAt: s.observedAt };
  }
  s.measurements.light.unit = '%'; // La démonstration utilise aussi un indice relatif.
  if (previousWater !== null && previousWater >= 20 && values.water < 20)
    addEvent(s, 'Réservoir inférieur à 20 % · réserve faible', 'warning', now);
  if (values.water < 15 && s.pump) {
    s.pump = false;
    addEvent(s, 'Pompe arrêtée · protection du réservoir', 'warning', now);
  }
  if (s.mode === 'automatic') {
    // Cycle simulé : 8 secondes toutes les 2 minutes, si l’eau suffit.
    const pump = Math.floor(seconds) % 120 >= 112 && values.water >= 15;
    if (pump !== s.pump)
      addEvent(
        s,
        pump ? 'Pompe activée · cycle automatique simulé' : 'Pompe arrêtée · cycle terminé',
        'info',
        now,
      );
    s.pump = pump;
  }
  s.history.push({ timestamp: now, ...values });
  // Garder les points récents et espacer les anciens pour limiter la mémoire.
  s.history = s.history.filter(
    (p, i, all) =>
      p.timestamp >= now - 86_400_000 &&
      (p.timestamp >= now - 3_600_000 ||
        i === 0 ||
        Math.floor(p.timestamp / 300_000) !== Math.floor(all[i - 1].timestamp / 300_000)),
  );
  return s;
}
