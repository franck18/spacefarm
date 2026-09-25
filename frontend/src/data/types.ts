// Définit et vérifie le format des données reçues du Pi.
import { z } from 'zod';

const number = z.number().finite();
const reading = z.object({
  value: number.nullable(),
  quality: z.enum(['ok', 'error', 'stale']),
  observedAt: z.string().datetime(),
  unit: z.string().optional(),
});
export const snapshotSchema = z.object({
  schemaVersion: z.literal(1),
  source: z.enum(['mock', 'live']),
  observedAt: z.string().datetime(),
  mode: z.enum(['automatic', 'manual', 'unconfigured']),
  measurements: z.object({
    temperature: reading,
    humidity: reading,
    light: reading,
    water: reading,
  }),
  cultivation: z
    .object({
      distance_plante: reading,
      hauteur_plante: reading,
      servo: reading,
      ventilateur: reading,
    })
    .optional(),
  pump: z.boolean().nullable(),
  lighting: z.boolean().nullable(),
  actuatorFeedback: z.enum(['simulated', 'commanded', 'measured', 'unavailable']),
  reservoirLiters: number.nonnegative().nullable(),
  reservoirCapacity: number.positive().nullable(),
  scenario: z.object({
    active: z.boolean(),
    referenceLiters: number.nonnegative().nullable(),
    fraction: number.min(0).max(1),
  }),
  system: z.object({
    hostname: z.string(),
    model: z.string(),
    os: z.string(),
    uptimeSeconds: number.nonnegative().nullable(),
    cpuTemperature: number.nullable(),
    memoryUsedPercent: number.min(0).max(100).nullable(),
    controlsAvailable: z.boolean(),
  }),
  history: z.array(
    z.object({
      timestamp: number,
      temperature: number.nullable(),
      humidity: number.nullable(),
      light: number.nullable(),
      water: number.nullable(),
    }),
  ),
  events: z.array(
    z.object({
      id: z.string(),
      timestamp: number,
      kind: z.enum(['info', 'success', 'warning']),
      message: z.string(),
    }),
  ),
});
export type Snapshot = z.infer<typeof snapshotSchema>;
export type Metric = keyof Snapshot['measurements'];
export type FarmEvent = Snapshot['events'][number];
export type Command =
  | { type: 'mode'; value: 'automatic' | 'manual' }
  | { type: 'pump' | 'lighting' | 'crisis'; value: boolean }
  | { type: 'reset' };
export interface FarmProvider {
  kind: 'mock' | 'api';
  read(): Promise<Snapshot>;
  command(command: Command): Promise<Snapshot>;
}

export const metricInfo = {
  temperature: {
    label: 'Température',
    unit: '°C',
    decimals: 0,
    min: 18,
    max: 28,
    domain: [18, 28] as [number, number],
  },
  humidity: {
    label: 'Humidité de l’air',
    unit: '%',
    decimals: 0,
    min: 45,
    max: 75,
    domain: [35, 85] as [number, number],
  },
  light: {
    label: 'Luminosité relative',
    unit: '%',
    decimals: 0,
    min: 0,
    max: 100,
    domain: [0, 100] as [number, number],
  },
  water: {
    label: 'Réservoir',
    unit: '%',
    decimals: 0,
    min: 20,
    max: 100,
    domain: [0, 100] as [number, number],
  },
};
export const formatNumber = (value: number, digits = 0) =>
  value.toLocaleString('fr-FR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
// Les cartes et les graphiques partagent les mêmes unités.
export const getMetricInfo = (key: Metric, _data: Snapshot) => metricInfo[key];
export const formatTime = (value: string | number) =>
  new Date(value).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
