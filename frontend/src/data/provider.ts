// Choisit la source : API réelle ou simulation locale.
import { applyCommand, advanceSnapshot, createSnapshot } from './engine';
import { snapshotSchema, type Command, type FarmProvider, type Snapshot } from './types';

// La simulation reste dans le navigateur.
function createMockProvider(): FarmProvider {
  let started = Date.now();
  let snapshot = createSnapshot(started);
  let manualPumpStarted: number | null = null;
  return {
    kind: 'mock',
    async read() {
      const now = Date.now();
      snapshot = advanceSnapshot(snapshot, now, started);
      if (manualPumpStarted !== null && now - manualPumpStarted >= 10_000 && snapshot.pump) {
        snapshot = applyCommand(snapshot, { type: 'pump', value: false }, now);
        snapshot.events[0].message = 'Pompe arrêtée · limite de démonstration de 10 s';
        manualPumpStarted = null;
      }
      return structuredClone(snapshot);
    },
    async command(command) {
      snapshot = applyCommand(snapshot, command);
      if (command.type === 'pump') manualPumpStarted = command.value ? Date.now() : null;
      if (command.type === 'mode' || command.type === 'reset') manualPumpStarted = null;
      if (command.type === 'reset') started = Date.now();
      return structuredClone(snapshot);
    },
  };
}

// Le Pi reste la source des mesures et des commandes réelles.
function createApiProvider(): FarmProvider {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
  const request = async (path: string, body?: unknown): Promise<Snapshot> => {
    const response = await fetch(`${base}/api/${path}`, {
      method: body ? 'POST' : 'GET',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error(`L’API a refusé la requête (${response.status}).`);
    // Refuser une réponse incomplète plutôt que montrer de fausses valeurs.
    const result = snapshotSchema.safeParse(await response.json());
    if (!result.success) throw new Error('Réponse API invalide : vérifier le contrat des données.');
    if (result.data.source !== 'live')
      throw new Error('L’API ne fournit pas de données identifiées comme réelles.');
    return result.data;
  };
  return {
    kind: 'api',
    read: () => request('state'),
    command: (command: Command) => {
      if (command.type === 'reset')
        return Promise.reject(new Error('Réinitialisation réservée à la démonstration.'));
      if (command.type === 'mode') return request('mode', { mode: command.value });
      if (command.type === 'crisis')
        return request('scenario', {
          active: command.value,
          availableWaterFraction: command.value ? 0.4 : 1,
        });
      return request('actuators', { actuator: command.type, enabled: command.value });
    },
  };
}

const requestedSource = new URLSearchParams(window.location.search).get('source');
export const provider =
  (requestedSource ?? import.meta.env.VITE_DATA_SOURCE) === 'mock'
    ? createMockProvider()
    : createApiProvider();
