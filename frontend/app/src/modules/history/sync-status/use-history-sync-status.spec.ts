import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistorySyncStatus } from './use-history-sync-status';

interface Summary {
  undecodedTxCount: number;
}

const HOUR_MS = 60 * 60 * 1000;

const processing = ref<boolean>(false);
const hasTxAccounts = ref<boolean>(false);
const isNeverQueried = ref<boolean>(false);
const isOutOfSync = ref<boolean>(false);
const earliestQueriedTimestamp = ref<number>(0);
const transactionStatusSummary = ref<Summary | undefined>(undefined);
const appVersion = ref<string>('1.40.0');
const dismissalThresholdMs = ref<number>(4 * HOUR_MS);
const minOutOfSyncPeriodMs = ref<number>(0);
const loggedUserId = ref<string | undefined>('user1');

vi.mock('@/modules/auth/use-logged-user-identifier', () => ({
  useLoggedUserIdentifier: (): object => loggedUserId,
}));

vi.mock('@/modules/history/sync-status/use-transaction-status-check', () => ({
  useTransactionStatusCheck: (): object => ({
    earliestQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync,
    processing,
  }),
}));

vi.mock('@/modules/history/sync-status/use-history-query-indicator-settings', () => ({
  useHistoryQueryIndicatorSettings: (): object => ({ dismissalThresholdMs, minOutOfSyncPeriodMs }),
}));

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: (): object => ({ transactionStatusSummary }),
}));

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): object => ({ appVersion }),
}));

/** What reached storage, read after the tick `useLocalStorage` writes on. */
async function storedStatus(): Promise<{ lastDismissedTs: number; lastUsedVersion: string | null }> {
  await nextTick();
  return JSON.parse(localStorage.getItem('user1.rotki_query_status') ?? 'null');
}

describe('useHistorySyncStatus', () => {
  beforeEach(() => {
    localStorage.clear();
    set(loggedUserId, 'user1');
    set(processing, false);
    set(hasTxAccounts, false);
    set(isOutOfSync, false);
    set(earliestQueriedTimestamp, 0);
    set(transactionStatusSummary, undefined);
    set(appVersion, '1.40.0');
  });

  describe('outOfSync', () => {
    it('should be false without accounts', () => {
      set(isOutOfSync, true);
      const { outOfSync } = useHistorySyncStatus();
      expect(get(outOfSync)).toBe(false);
    });

    it('should mirror the out-of-sync check when accounts exist', () => {
      set(hasTxAccounts, true);
      set(isOutOfSync, true);
      const { outOfSync } = useHistorySyncStatus();
      expect(get(outOfSync)).toBe(true);
    });
  });

  describe('longQuery', () => {
    it('should be true when queried long ago with no undecoded transactions', () => {
      set(hasTxAccounts, true);
      set(transactionStatusSummary, { undecodedTxCount: 0 });
      const { longQuery } = useHistorySyncStatus();
      expect(get(longQuery)).toBe(true);
    });

    it('should be false without accounts, however long ago history was queried', () => {
      set(transactionStatusSummary, { undecodedTxCount: 0 });
      const { longQuery } = useHistorySyncStatus();
      expect(get(longQuery)).toBe(false);
    });

    it('should be false when there are undecoded transactions', () => {
      set(hasTxAccounts, true);
      set(transactionStatusSummary, { undecodedTxCount: 5 });
      const { longQuery } = useHistorySyncStatus();
      expect(get(longQuery)).toBe(false);
    });
  });

  describe('dismissal', () => {
    it('should count as dismissed recently until the threshold passes', () => {
      vi.useFakeTimers({ now: new Date('2026-09-18T12:00:00Z') });
      try {
        const { dismiss, dismissedRecently } = useHistorySyncStatus();
        expect(get(dismissedRecently)).toBe(false);

        dismiss();
        expect(get(dismissedRecently)).toBe(true);

        vi.advanceTimersByTime(4 * HOUR_MS);
        expect(get(dismissedRecently)).toBe(false);
      }
      finally {
        vi.useRealTimers();
      }
    });

    it('should clear the dismissal on reset', async () => {
      const { dismiss, dismissedRecently, resetQueryStatus } = useHistorySyncStatus();
      dismiss();
      expect((await storedStatus()).lastDismissedTs).toBeGreaterThan(0);

      resetQueryStatus();
      expect(get(dismissedRecently)).toBe(false);
      expect(await storedStatus()).toEqual({ lastDismissedTs: 0, lastUsedVersion: null });
    });

    it('should follow the logged-in user rather than the one it was created under', async () => {
      localStorage.setItem('user2.rotki_query_status', JSON.stringify({ lastDismissedTs: Date.now(), lastUsedVersion: '1.40.0' }));
      set(loggedUserId, undefined);
      const { dismissedRecently } = useHistorySyncStatus();
      expect(get(dismissedRecently)).toBe(false);

      set(loggedUserId, 'user2');
      await nextTick();

      expect(get(dismissedRecently)).toBe(true);
    });
  });

  describe('recordAppVersion', () => {
    it('should clear the dismissal and mark just updated on a minor update', async () => {
      const { dismiss, dismissedRecently, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      set(appVersion, '1.41.0');

      recordAppVersion();

      expect(get(justUpdated)).toBe(true);
      expect(get(dismissedRecently)).toBe(false);
      expect((await storedStatus()).lastUsedVersion).toBe('1.41.0');
    });

    it('should keep the dismissal and only record the version on a patch update', async () => {
      const { dismiss, dismissedRecently, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      set(appVersion, '1.40.1');

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect(get(dismissedRecently)).toBe(true);
      expect((await storedStatus()).lastUsedVersion).toBe('1.40.1');
    });

    it('should leave a dismissal alone when the version is the one already recorded', async () => {
      const { dismiss, dismissedRecently, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      const recorded = await storedStatus();

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect(get(dismissedRecently)).toBe(true);
      expect(await storedStatus()).toEqual(recorded);
    });

    it('should not mark just updated on a first run with no recorded version', async () => {
      const { justUpdated, recordAppVersion } = useHistorySyncStatus();

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect((await storedStatus()).lastUsedVersion).toBe('1.40.0');
    });
  });
});
