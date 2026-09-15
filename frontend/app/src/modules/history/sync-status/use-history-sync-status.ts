import type { ComputedRef, Ref } from 'vue';
import { get, isDefined, set } from '@vueuse/shared';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { isMajorOrMinorUpdate } from '@/modules/history/sync-status/is-major-or-minor-update';
import { useHistoryQueryIndicatorSettings } from '@/modules/history/sync-status/use-history-query-indicator-settings';
import { useTransactionStatusCheck } from '@/modules/history/sync-status/use-transaction-status-check';
import { useHistoryStore } from '@/modules/history/use-history-store';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

/** How often a dismissal is re-checked against its threshold. */
const DISMISSAL_TICK_MS = 60_000;

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
  /** Dismissed within the dismissal threshold, so it is not asking for attention right now. */
  dismissedRecently: ComputedRef<boolean>;
  dismiss: () => void;
  resetQueryStatus: () => void;
  /**
   * Compares the running app version with the one recorded last session.
   *
   * @remarks
   * A major or minor update clears the dismissal and sets `justUpdated`; a patch update only records
   * the version. Call it once per session, from the surface that shows the status.
   */
  recordAppVersion: () => void;
}

interface QueryStatusDismissal {
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

/**
 * Whether the user's history is out of sync, when it was last queried, and whether the user set that
 * aside recently.
 *
 * @remarks
 * Progress for work in flight is the task dock's; this only says what state history was left in.
 */
export function useHistorySyncStatus(): UseHistorySyncStatusReturn {
  const userId = useLoggedUserIdentifier();

  const queryStatus: Ref<QueryStatusDismissal> = useLocalStorage<QueryStatusDismissal>(() => `${get(userId)}.rotki_query_status`, {
    lastDismissedTs: 0,
    lastUsedVersion: null,
  });

  const justUpdated = shallowRef<boolean>(false);

  const { appVersion } = storeToRefs(useMainStore());
  const { transactionStatusSummary } = storeToRefs(useHistoryStore());

  const {
    earliestQueriedTimestamp: lastQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync,
    processing,
  } = useTransactionStatusCheck();

  const { dismissalThresholdMs } = useHistoryQueryIndicatorSettings();

  const now = useNow({ interval: DISMISSAL_TICK_MS });

  const outOfSync = computed<boolean>(() => get(hasTxAccounts) && get(isOutOfSync));

  const longQuery = computed<boolean>(() => {
    if (!get(hasTxAccounts))
      return false;

    const status = get(transactionStatusSummary);
    return isDefined(status) && status.undecodedTxCount === 0 && Date.now() - get(lastQueriedTimestamp) > HUNDRED_EIGHTY_DAYS;
  });

  const dismissedRecently = computed<boolean>(() =>
    get(now).getTime() - get(queryStatus).lastDismissedTs < get(dismissalThresholdMs),
  );

  function dismiss(): void {
    set(queryStatus, {
      lastDismissedTs: Date.now(),
      lastUsedVersion: get(appVersion),
    });
  }

  function resetQueryStatus(): void {
    set(queryStatus, {
      lastDismissedTs: 0,
      lastUsedVersion: null,
    });
  }

  function recordAppVersion(): void {
    const currentVersion = get(appVersion);
    const { lastDismissedTs, lastUsedVersion } = get(queryStatus);

    if (!currentVersion || currentVersion === lastUsedVersion)
      return;

    if (isMajorOrMinorUpdate(currentVersion, lastUsedVersion)) {
      set(queryStatus, { lastDismissedTs: 0, lastUsedVersion: currentVersion });
      set(justUpdated, true);
      return;
    }

    set(queryStatus, { lastDismissedTs, lastUsedVersion: currentVersion });
  }

  return {
    dismiss,
    dismissedRecently,
    hasTxAccounts,
    isNeverQueried,
    justUpdated: readonly(justUpdated),
    lastQueriedTimestamp,
    longQuery,
    outOfSync,
    processing,
    recordAppVersion,
    resetQueryStatus,
  };
}
