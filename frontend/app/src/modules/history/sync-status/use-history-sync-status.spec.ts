import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistorySyncStatus } from './use-history-sync-status';

interface Summary {
  undecodedTxCount: number;
}

const HOUR_MS = 60 * 60 * 1000;

const SYNCED_AT = Date.UTC(2026, 8, 15, 10, 30);

const processing = ref<boolean>(false);
const hasTxAccounts = ref<boolean>(false);
const isNeverQueried = ref<boolean>(false);
const isOutOfSync = ref<boolean>(false);
const earliestQueriedTimestamp = ref<number>(0);
const transactionStatusSummary = ref<Summary | undefined>(undefined);
const appVersion = ref<string>('1.40.0');
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
  useHistoryQueryIndicatorSettings: (): object => ({ minOutOfSyncPeriodMs }),
}));

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: (): object => ({ transactionStatusSummary }),
}));

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): object => ({ appVersion }),
}));

/** What reached storage, read after the tick `useLocalStorage` writes on. */
async function storedStatus(): Promise<{ lastUsedVersion: string | null } | null> {
  await nextTick();
  return JSON.parse(localStorage.getItem('user1.rotki_query_status') ?? 'null');
}

describe('useHistorySyncStatus', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
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
    it('should stay dismissed while history has not moved, however long that takes', () => {
      vi.useFakeTimers({ now: new Date('2026-09-18T12:00:00Z') });
      try {
        set(earliestQueriedTimestamp, SYNCED_AT);
        const { dismiss, dismissed } = useHistorySyncStatus();
        expect(get(dismissed)).toBe(false);

        dismiss();
        vi.advanceTimersByTime(7 * 24 * HOUR_MS);

        expect(get(dismissed)).toBe(true);
      }
      finally {
        vi.useRealTimers();
      }
    });

    it('should come back once a sync moves the last-queried time', () => {
      set(earliestQueriedTimestamp, SYNCED_AT);
      const { dismiss, dismissed } = useHistorySyncStatus();
      dismiss();

      set(earliestQueriedTimestamp, SYNCED_AT + HOUR_MS);

      expect(get(dismissed)).toBe(false);
    });

    it('should come back when a new source brings an older last-queried time', () => {
      set(earliestQueriedTimestamp, SYNCED_AT);
      const { dismiss, dismissed } = useHistorySyncStatus();
      dismiss();

      set(earliestQueriedTimestamp, 0);

      expect(get(dismissed)).toBe(false);
    });

    it('should not outlive the session or reach storage', async () => {
      set(earliestQueriedTimestamp, SYNCED_AT);
      useHistorySyncStatus().dismiss();
      expect(await storedStatus()).toEqual({ lastUsedVersion: null });

      setActivePinia(createPinia());

      expect(get(useHistorySyncStatus().dismissed)).toBe(false);
    });

    it('should clear the dismissal on reset', () => {
      set(earliestQueriedTimestamp, SYNCED_AT);
      const { dismiss, dismissed, resetDismissal } = useHistorySyncStatus();
      dismiss();

      resetDismissal();

      expect(get(dismissed)).toBe(false);
    });
  });

  describe('recordAppVersion', () => {
    it('should follow the logged-in user rather than the one it was created under', async () => {
      localStorage.setItem('user2.rotki_query_status', JSON.stringify({ lastUsedVersion: '1.40.0' }));
      set(loggedUserId, undefined);
      set(appVersion, '1.41.0');
      const { justUpdated, recordAppVersion } = useHistorySyncStatus();

      set(loggedUserId, 'user2');
      await nextTick();
      recordAppVersion();

      expect(get(justUpdated)).toBe(true);
    });

    it('should clear the dismissal and mark just updated on a minor update', async () => {
      localStorage.setItem('user1.rotki_query_status', JSON.stringify({ lastUsedVersion: '1.40.0' }));
      const { dismiss, dismissed, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      set(appVersion, '1.41.0');

      recordAppVersion();

      expect(get(justUpdated)).toBe(true);
      expect(get(dismissed)).toBe(false);
      expect((await storedStatus())?.lastUsedVersion).toBe('1.41.0');
    });

    it('should keep the dismissal and only record the version on a patch update', async () => {
      localStorage.setItem('user1.rotki_query_status', JSON.stringify({ lastUsedVersion: '1.40.0' }));
      const { dismiss, dismissed, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      set(appVersion, '1.40.1');

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect(get(dismissed)).toBe(true);
      expect((await storedStatus())?.lastUsedVersion).toBe('1.40.1');
    });

    it('should leave a dismissal alone when the version is the one already recorded', async () => {
      localStorage.setItem('user1.rotki_query_status', JSON.stringify({ lastUsedVersion: '1.40.0' }));
      const { dismiss, dismissed, justUpdated, recordAppVersion } = useHistorySyncStatus();
      dismiss();
      const recorded = await storedStatus();

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect(get(dismissed)).toBe(true);
      expect(await storedStatus()).toEqual(recorded);
    });

    it('should not mark just updated on a first run with no recorded version', async () => {
      const { justUpdated, recordAppVersion } = useHistorySyncStatus();

      recordAppVersion();

      expect(get(justUpdated)).toBe(false);
      expect((await storedStatus())?.lastUsedVersion).toBe('1.40.0');
    });
  });
});
