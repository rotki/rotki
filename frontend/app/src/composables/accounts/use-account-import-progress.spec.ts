import { beforeEach, describe, expect, it } from 'vitest';
import {
  TotalCannotBeNegativeError,
  TotalNotInitializedError,
  useAccountImportProgress,
} from '@/composables/accounts/use-account-import-progress';

describe('useAccountImportProgress', () => {
  let progressManager: ReturnType<typeof useAccountImportProgress>;

  beforeEach(() => {
    progressManager = useAccountImportProgress();
    progressManager.setTotal(0);
  });

  it('should initialize with default values', () => {
    const progress = get(progressManager.progress);
    expect(progress.total).toBe(0);
    expect(progress.current).toBe(0);
    expect(progress.skipped).toBe(0);
    expect(get(progressManager.importingAccounts)).toBe(false);
  });

  it('should set the total correctly', () => {
    progressManager.setTotal(5);
    expect(get(progressManager.progress).total).toBe(5);
    expect(get(progressManager.importingAccounts)).toBe(true);
  });

  it('should increment the current progress correctly', () => {
    progressManager.setTotal(3);
    progressManager.increment();
    const progress = get(progressManager.progress);
    expect(progress.current).toBe(1);
    expect(progress.skipped).toBe(0);
    expect(progress.total).toBe(3);
  });

  it('should add to skipped progress when skipping', () => {
    progressManager.setTotal(3);
    progressManager.skip();
    const progress = get(progressManager.progress);
    expect(progress.current).toBe(1);
    expect(progress.skipped).toBe(1);
    expect(progress.total).toBe(3);
  });

  it('should handle increment after skipping correctly', () => {
    progressManager.setTotal(3);
    progressManager.skip();
    progressManager.increment();
    const progress = get(progressManager.progress);
    expect(progress.current).toBe(2);
    expect(progress.skipped).toBe(1);
    expect(progress.total).toBe(3);
  });

  it('should return importingAccounts as true when total > 0', () => {
    progressManager.setTotal(1);
    expect(get(progressManager.importingAccounts)).toBe(true);
  });

  it('should return importingAccounts as false when total is 0', () => {
    progressManager.setTotal(0);
    expect(get(progressManager.importingAccounts)).toBe(false);
  });

  it('should throw an exception if setTotal is not called first', () => {
    expect(() => progressManager.increment()).throws(TotalNotInitializedError);
  });

  it('should handle resetting the progress', () => {
    progressManager.setTotal(5);
    progressManager.increment();
    progressManager.skip();
    let progress = get(progressManager.progress);
    expect(progress.current).toBe(2);
    progressManager.setTotal(0);
    progress = get(progressManager.progress);
    expect(progress.total).toBe(0);
    expect(progress.current).toBe(0);
    expect(get(progressManager.importingAccounts)).toBe(false);
  });

  it('should throw an exception if the setTotal is called with a negative number', () => {
    expect(() => progressManager.setTotal(-1)).throws(TotalCannotBeNegativeError);
  });
});
