import { describe, expect, it } from 'vitest';
import { advanceSnapshot, applyCommand, createSnapshot, waterPlan } from './engine';

describe('SpaceFarm demonstration decisions', () => {
  it('does not invent autonomy or run simulation commands on a real Pi snapshot', () => {
    const s = createSnapshot();
    s.source = 'live';
    s.reservoirLiters = null;
    s.reservoirCapacity = null;
    expect(waterPlan(s).autonomy).toBeNull();
    expect(waterPlan(s).meetsTarget).toBe(false);
    expect(() => applyCommand(s, { type: 'pump', value: true })).toThrow('matériel réel');
  });
  it('requires manual mode to command an actuator', () => {
    const s = createSnapshot();
    expect(() => applyCommand(s, { type: 'pump', value: true })).toThrow('manuel');
    const manual = applyCommand(s, { type: 'mode', value: 'manual' });
    expect(applyCommand(manual, { type: 'pump', value: true }).pump).toBe(true);
    expect(s.mode).toBe('automatic');
  });
  it('blocks irrigation when the reservoir is low or unknown', () => {
    const s = applyCommand(createSnapshot(), { type: 'mode', value: 'manual' });
    for (const value of [14, null]) {
      s.measurements.water.value = value;
      expect(() => applyCommand(s, { type: 'pump', value: true })).toThrow('bloquée');
    }
  });
  it('keeps measured water separate from the 40 percent scenario', () => {
    const s = applyCommand(createSnapshot(), { type: 'crisis', value: true });
    expect(s.measurements.water.value).toBe(76);
    expect(waterPlan(s).available).toBeCloseTo(3.04);
    expect(waterPlan(s).required).toBeCloseTo(3);
    expect(waterPlan(s).meetsTarget).toBe(true);
    s.scenario.referenceLiters = 5;
    expect(waterPlan(s).meetsTarget).toBe(false);
  });
  it('restores normal budget after ending a crisis', () => {
    const s = applyCommand(applyCommand(createSnapshot(), { type: 'crisis', value: true }), {
      type: 'crisis',
      value: false,
    });
    expect(waterPlan(s).available).toBe(s.reservoirLiters);
    expect(waterPlan(s).daily).toBeCloseTo(2.4);
  });
  it('stops a manual pump when switching back to automatic', () => {
    const manual = applyCommand(createSnapshot(), { type: 'mode', value: 'manual' });
    const running = applyCommand(manual, { type: 'pump', value: true });
    expect(applyCommand(running, { type: 'mode', value: 'automatic' }).pump).toBe(false);
  });
  it('switches lighting measurements and advances real timestamps', () => {
    const start = Date.now();
    let s = applyCommand(createSnapshot(start), { type: 'mode', value: 'manual' });
    s = applyCommand(s, { type: 'lighting', value: false });
    const next = advanceSnapshot(s, start + 3000, start);
    expect(next.measurements.light.value).toBe(2.4);
    expect(new Date(next.observedAt).getTime()).toBe(start + 3000);
    expect(next.history.at(-1)?.light).toBe(2.4);
  });
  it('runs a bounded automatic irrigation cycle', () => {
    const start = Date.now();
    const running = advanceSnapshot(createSnapshot(start), start + 114_000, start);
    expect(running.pump).toBe(true);
    expect(advanceSnapshot(running, start + 120_000, start).pump).toBe(false);
  });
});
