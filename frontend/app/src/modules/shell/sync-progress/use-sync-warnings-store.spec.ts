import { beforeEach, describe, expect, it } from 'vitest';
import { SyncWarningSource, useSyncWarningsStore } from './use-sync-warnings-store';

describe('useSyncWarningsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should start with no warnings', () => {
    const store = useSyncWarningsStore();
    expect(get(store.warnings)).toEqual([]);
    expect(get(store.hasWarnings)).toBe(false);
  });

  it('should add a warning and expose hasWarnings', () => {
    const store = useSyncWarningsStore();
    store.addWarning({
      key: 'block_productions',
      message: 'Block production skipped',
      source: SyncWarningSource.ONLINE_EVENTS,
    });

    expect(get(store.warnings)).toHaveLength(1);
    expect(get(store.hasWarnings)).toBe(true);
  });

  it('should dedupe warnings by source and key', () => {
    const store = useSyncWarningsStore();
    const warning = {
      key: 'block_productions',
      message: 'first',
      source: SyncWarningSource.ONLINE_EVENTS,
    };
    store.addWarning(warning);
    store.addWarning({ ...warning, message: 'second' });

    expect(get(store.warnings)).toHaveLength(1);
    expect(get(store.warnings)[0].message).toBe('first');
  });

  it('should keep distinct keys separate', () => {
    const store = useSyncWarningsStore();
    store.addWarning({
      key: 'block_productions',
      message: 'a',
      source: SyncWarningSource.ONLINE_EVENTS,
    });
    store.addWarning({
      key: 'eth_withdrawals',
      message: 'b',
      source: SyncWarningSource.ONLINE_EVENTS,
    });

    expect(get(store.warnings)).toHaveLength(2);
  });

  it('should clear all warnings on reset', () => {
    const store = useSyncWarningsStore();
    store.addWarning({
      key: 'block_productions',
      message: 'x',
      source: SyncWarningSource.ONLINE_EVENTS,
    });
    store.resetWarnings();

    expect(get(store.warnings)).toEqual([]);
    expect(get(store.hasWarnings)).toBe(false);
  });
});
