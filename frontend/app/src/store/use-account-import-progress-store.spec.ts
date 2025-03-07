import {
  TotalCannotBeNegativeError,
  TotalNotInitializedError,
  useAccountImportProgressStore,
} from '@/store/use-account-import-progress-store';
import { beforeEach, describe, expect, it } from 'vitest';

describe('useAccountImportProgress', () => {
  let store: ReturnType<typeof useAccountImportProgressStore>;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useAccountImportProgressStore();
    store.setTotal(0);
  });

  it('should initialize with default values', () => {
    const progress = get(store.progress);
    expect(progress.total).toBe(0);
    expect(progress.current).toBe(0);
    expect(progress.skipped).toBe(0);
    expect(get(store.importingAccounts)).toBe(false);
  });

  it('should set the total correctly', () => {
    store.setTotal(5);
    expect(get(store.progress).total).toBe(5);
    expect(get(store.importingAccounts)).toBe(true);
  });

  it('should increment the current progress correctly', () => {
    store.setTotal(3);
    store.increment();
    const progress = get(store.progress);
    expect(progress.current).toBe(1);
    expect(progress.skipped).toBe(0);
    expect(progress.total).toBe(3);
  });

  it('should add to skipped progress when skipping', () => {
    store.setTotal(3);
    store.skip();
    const progress = get(store.progress);
    expect(progress.current).toBe(1);
    expect(progress.skipped).toBe(1);
    expect(progress.total).toBe(3);
  });

  it('should handle increment after skipping correctly', () => {
    store.setTotal(3);
    store.skip();
    store.increment();
    const progress = get(store.progress);
    expect(progress.current).toBe(2);
    expect(progress.skipped).toBe(1);
    expect(progress.total).toBe(3);
  });

  it('should return importingAccounts as true when total > 0', () => {
    store.setTotal(1);
    expect(get(store.importingAccounts)).toBe(true);
  });

  it('should return importingAccounts as false when total is 0', () => {
    store.setTotal(0);
    expect(get(store.importingAccounts)).toBe(false);
  });

  it('should throw an exception if increment is called before setTotal', () => {
    expect(() => store.increment()).throws(TotalNotInitializedError);
  });

  it('should throw an exception if skip is called before setTotal', () => {
    expect(() => store.skip()).throws(TotalNotInitializedError);
  });

  it('should handle resetting the progress', () => {
    store.setTotal(5);
    store.increment();
    store.skip();
    let progress = get(store.progress);
    expect(progress.current).toBe(2);
    store.setTotal(0);
    progress = get(store.progress);
    expect(progress.total).toBe(0);
    expect(progress.current).toBe(0);
    expect(get(store.importingAccounts)).toBe(false);
  });

  it('should return the percentage correctly', () => {
    store.setTotal(10);
    store.increment();
    store.skip();
    expect(get(store.progressPercentage)).toBe(20);
  });

  it('should throw an exception if the setTotal is called with a negative number', () => {
    expect(() => store.setTotal(-1)).throws(TotalCannotBeNegativeError);
  });
});
