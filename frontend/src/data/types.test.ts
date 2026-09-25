import { describe, expect, it } from 'vitest';
import { advanceSnapshot, createSnapshot } from './engine';
import { getMetricInfo, snapshotSchema } from './types';

describe('API contract', () => {
  it('keeps simulated light readings and history in percent after refresh', () => {
    const start = Date.now();
    const initial = createSnapshot(start);
    for (const snapshot of [initial, advanceSnapshot(initial, start + 3000, start)]) {
      expect(snapshot.measurements.light.unit).toBe('%');
      expect(getMetricInfo('light', snapshot).unit).toBe('%');
      expect(snapshot.measurements.light.value).toBeGreaterThanOrEqual(0);
      expect(snapshot.measurements.light.value).toBeLessThanOrEqual(100);
      expect(
        snapshot.history.every((p) => p.light !== null && p.light >= 0 && p.light <= 100),
      ).toBe(true);
    }
  });
  it('accepts unavailable measurements without turning them into zero', () => {
    const snapshot = createSnapshot();
    snapshot.measurements.temperature = {
      value: null,
      quality: 'error',
      observedAt: snapshot.observedAt,
    };
    const parsed = snapshotSchema.parse(snapshot);
    expect(parsed.measurements.temperature.value).toBeNull();
  });
  it('rejects malformed timestamps, non-finite data, and incomplete payloads', () => {
    expect(snapshotSchema.safeParse({ temperature: 23 }).success).toBe(false);
    const snapshot = createSnapshot();
    snapshot.observedAt = 'yesterday';
    expect(snapshotSchema.safeParse(snapshot).success).toBe(false);
    snapshot.observedAt = new Date().toISOString();
    snapshot.measurements.temperature.value = Number.NaN;
    expect(snapshotSchema.safeParse(snapshot).success).toBe(false);
  });
});
