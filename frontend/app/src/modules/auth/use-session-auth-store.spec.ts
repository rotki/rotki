import type { DbUpgradeStatusData } from '@/modules/core/messaging/types';
import { get } from '@vueuse/shared';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from './use-session-auth-store';

const START = new Date('2026-11-27T12:00:00Z').getTime();

function upgrade(toVersion: number, currentStep: number): DbUpgradeStatusData {
  return { currentUpgrade: { currentStep, description: null, toVersion, totalSteps: 4 }, startVersion: 52, targetVersion: 54 };
}

describe('modules/auth/use-session-auth-store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.setSystemTime(START);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should keep the start time a version was first reported at across its later steps', () => {
    const store = useSessionAuthStore();
    const { dbUpgradeVersionTimes, upgradeStartedAt } = storeToRefs(store);

    store.updateDbUpgradeStatus(upgrade(52, 1));
    vi.advanceTimersByTime(3000);
    store.updateDbUpgradeStatus(upgrade(52, 2));
    vi.advanceTimersByTime(2000);
    store.updateDbUpgradeStatus(upgrade(53, 1));

    expect(get(dbUpgradeVersionTimes)).toEqual({ 52: START, 53: START + 5000 });
    expect(get(upgradeStartedAt)).toBe(START);
  });

  it('should start the run at the earliest message of either a DB upgrade or a data migration', () => {
    const store = useSessionAuthStore();
    const { upgradeStartedAt } = storeToRefs(store);

    expect(get(upgradeStartedAt)).toBeNull();

    store.updateDataMigrationStatus({ currentMigration: { currentStep: 0, description: null, totalSteps: 0, version: 18 }, startVersion: 18, targetVersion: 18 });
    vi.advanceTimersByTime(1000);
    store.updateDbUpgradeStatus(upgrade(52, 1));

    expect(get(upgradeStartedAt)).toBe(START);
  });

  it('should only record a failure while an upgrade is on screen, and clear it with the rest', () => {
    const store = useSessionAuthStore();
    const { upgradeFailure, upgradeStartedAt, upgradeVisible } = storeToRefs(store);

    expect(store.failUpgrade('wrong password')).toBe(false);
    expect(get(upgradeFailure)).toBeNull();

    store.updateDbUpgradeStatus(upgrade(52, 1));
    expect(store.failUpgrade('Failed at database upgrade from version 51 to 52: boom')).toBe(true);
    expect(get(upgradeFailure)).toBe('Failed at database upgrade from version 51 to 52: boom');

    store.clearUpgradeMessages();

    expect(get(upgradeVisible)).toBe(false);
    expect(get(upgradeFailure)).toBeNull();
    expect(get(upgradeStartedAt)).toBeNull();
  });
});
