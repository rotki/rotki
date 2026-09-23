import type { ComputedRef, Ref } from 'vue';
import { get, isDefined, set } from '@vueuse/shared';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { isMajorOrMinorUpdate } from '@/modules/history/sync-status/is-major-or-minor-update';
import { useHistorySyncDismissalStore } from '@/modules/history/sync-status/use-history-sync-dismissal-store';
import { useTransactionStatusCheck } from '@/modules/history/sync-status/use-transaction-status-check';
import { useHistoryStore } from '@/modules/history/use-history-store';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface UseHistorySyncStatusReturn {
  /** The user has EVM accounts or exchanges, the sources this status is about. */
  hasTxAccounts: ComputedRef<boolean>;
  /** The user has history sources and at least one was never queried, or not within the out-of-sync period. */
  outOfSync: ComputedRef<boolean>;
  isNeverQueried: ComputedRef<boolean>;
  /** When history was last queried, in milliseconds. `0` when it never was. */
  lastQueriedTimestamp: ComputedRef<number>;
  /** Last queried over 180 days ago, with nothing left undecoded. */
  longQuery: ComputedRef<boolean>;
  /** A major or minor app update was recorded by {@link UseHistorySyncStatusReturn.recordAppVersion}. */
  justUpdated: Readonly<Ref<boolean>>;
  processing: Ref<boolean>;
  /**
   * The user set this state of history aside, so it is not asking for attention right now.
   *
   * @remarks
   * Bound to the last-queried timestamp the user dismissed at, never to a timer: it holds until a
   * sync moves that timestamp or a new source brings an older one, and ends with the session.
   */
  dismissed: ComputedRef<boolean>;
  dismiss: () => void;
  /** Brings a dismissed reminder back. */
  resetDismissal: () => void;
  /**
   * Compares the running app version with the one recorded last session.
   *
   * @remarks
   * A major or minor update clears the dismissal and sets `justUpdated`; a patch update only records
   * the version. Call it once per session, from the surface that shows the status.
   */
  recordAppVersion: () => void;
}

interface RecordedVersion {
  lastUsedVersion: string | null;
}

/**
 * Whether the user's history is out of sync, when it was last queried, and whether the user set that
 * aside.
 *
 * @remarks
 * Progress for work in flight is the task dock's; this only says what state history was left in.
 */
export function useHistorySyncStatus(): UseHistorySyncStatusReturn {
  const userId = useLoggedUserIdentifier();

  const recordedVersion: Ref<RecordedVersion> = useLocalStorage<RecordedVersion>(() => `${get(userId)}.rotki_query_status`, {
    lastUsedVersion: null,
  });

  const justUpdated = shallowRef<boolean>(false);

  const { appVersion } = storeToRefs(useMainStore());
  const { transactionStatusSummary } = storeToRefs(useHistoryStore());
  const dismissalStore = useHistorySyncDismissalStore();
  const { dismissedAt } = storeToRefs(dismissalStore);
  const { setDismissedAt } = dismissalStore;

  const {
    earliestQueriedTimestamp: lastQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync,
    processing,
  } = useTransactionStatusCheck();

  const outOfSync = computed<boolean>(() => get(hasTxAccounts) && get(isOutOfSync));

  const longQuery = computed<boolean>(() => {
    if (!get(hasTxAccounts))
      return false;

    const status = get(transactionStatusSummary);
    return isDefined(status) && status.undecodedTxCount === 0 && Date.now() - get(lastQueriedTimestamp) > HUNDRED_EIGHTY_DAYS;
  });

  const dismissed = computed<boolean>(() => {
    const at = get(dismissedAt);
    return at !== undefined && at === get(lastQueriedTimestamp);
  });

  function dismiss(): void {
    setDismissedAt(get(lastQueriedTimestamp));
  }

  function resetDismissal(): void {
    setDismissedAt(undefined);
  }

  function recordAppVersion(): void {
    const currentVersion = get(appVersion);
    const { lastUsedVersion } = get(recordedVersion);

    if (!currentVersion || currentVersion === lastUsedVersion)
      return;

    set(recordedVersion, { lastUsedVersion: currentVersion });

    if (isMajorOrMinorUpdate(currentVersion, lastUsedVersion)) {
      resetDismissal();
      set(justUpdated, true);
    }
  }

  return {
    dismiss,
    dismissed,
    hasTxAccounts,
    isNeverQueried,
    justUpdated: readonly(justUpdated),
    lastQueriedTimestamp,
    longQuery,
    outOfSync,
    processing,
    recordAppVersion,
    resetDismissal,
  };
}
