import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { HISTORY_ISSUE_IDS, type useHistoryEventIssues as UseHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { PinnedNames } from '@/modules/session/types';

const state = {
  autoFixCount: ref(0),
  autoFixGroupIds: ref<string[]>([]),
  autoMatchLoading: ref(false),
  bridgeAutoMatchLoading: ref(false),
  dataIssuesCount: ref(0),
  fetchCounts: vi.fn<() => Promise<void>>(),
  fetchCustomizedEventDuplicates: vi.fn<() => Promise<void>>(),
  fetchUndecodedTransactionsBreakdown: vi.fn<() => Promise<void>>(),
  internalConflictsCount: ref(0),
  manualReviewCount: ref(0),
  manualReviewGroupIds: ref<string[]>([]),
  ignoredBridgesCount: ref(0),
  ignoredMovementsCount: ref(0),
  logged: ref(true),
  matchingAllowed: ref(true),
  processing: ref(false),
  refreshDataIssuesSummary: vi.fn<() => Promise<void>>(),
  refreshUnmatchedAssetMovements: vi.fn<() => Promise<void>>(),
  refreshUnmatchedBridgeTransactions: vi.fn<() => Promise<void>>(),
  trackedEntitiesLoading: ref(false),
  tracksNothing: ref(false),
  undecodedCount: ref(0),
  unmatchedBridgesCount: ref(0),
  unmatchedMovementsCount: ref(0),
};

vi.mock('@/modules/accounts/use-tracked-entities', () => ({
  useTrackedEntities: (): object => ({
    loading: state.trackedEntitiesLoading,
    tracksNothing: state.tracksNothing,
  }),
}));

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({
    autoMatchLoading: state.autoMatchLoading,
    ignoredCount: state.ignoredMovementsCount,
    loading: ref(false),
    refreshUnmatchedAssetMovements: state.refreshUnmatchedAssetMovements,
    unmatchedCount: state.unmatchedMovementsCount,
  }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({
    autoMatchLoading: state.bridgeAutoMatchLoading,
    ignoredCount: state.ignoredBridgesCount,
    loading: ref(false),
    refreshUnmatchedBridgeTransactions: state.refreshUnmatchedBridgeTransactions,
    unmatchedCount: state.unmatchedBridgesCount,
  }),
}));

vi.mock('@/modules/history/events/use-customized-event-duplicates', () => ({
  useCustomizedEventDuplicates: (): object => ({
    autoFixCount: state.autoFixCount,
    autoFixGroupIds: state.autoFixGroupIds,
    fetchCustomizedEventDuplicates: state.fetchCustomizedEventDuplicates,
    loading: ref(false),
    manualReviewCount: state.manualReviewCount,
    manualReviewGroupIds: state.manualReviewGroupIds,
  }),
}));

vi.mock('@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts', () => ({
  useInternalTxConflicts: (): object => ({
    fetchCounts: state.fetchCounts,
    issueCount: state.internalConflictsCount,
  }),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged: state.logged }),
}));

vi.mock('@/modules/premium/use-feature-access', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/premium/use-feature-access')>();
  return {
    ...original,
    useFeatureAccess: (): object => ({
      allowed: state.matchingAllowed,
      currentTier: ref('Free'),
      minimumTier: ref('Basic'),
      premium: ref(false),
    }),
  };
});

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): object => ({ processing: state.processing }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): object => ({
    actionableCount: state.dataIssuesCount,
    refreshSummary: state.refreshDataIssuesSummary,
  }),
}));

vi.mock('@/modules/history/events/tx/use-undecoded-transactions-count', () => ({
  useUndecodedTransactionsCount: (): object => ({
    fetchUndecodedTransactionsBreakdown: state.fetchUndecodedTransactionsBreakdown,
    undecodedCount: state.undecodedCount,
  }),
}));

/**
 * Imports the composable under test with its module state discarded.
 *
 * @remarks
 * `scanned` lives on the module, shared by the trigger and the panel, so a test that reuses the
 * import inherits whether an earlier one had already scanned and its pre-scan assertions pass
 * for the wrong reason.
 */
async function loadComposable(): Promise<typeof UseHistoryEventIssues> {
  vi.resetModules();
  const module = await import('@/modules/history/events/actions-center/use-history-event-issues');
  return module.useHistoryEventIssues;
}

describe('useHistoryEventIssues', () => {
  let useHistoryEventIssues: typeof UseHistoryEventIssues;

  beforeEach(async () => {
    vi.clearAllMocks();
    useHistoryEventIssues = await loadComposable();
    set(state.autoFixCount, 0);
    set(state.autoFixGroupIds, []);
    set(state.autoMatchLoading, false);
    set(state.bridgeAutoMatchLoading, false);
    set(state.dataIssuesCount, 0);
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    set(state.internalConflictsCount, 0);
    set(state.manualReviewCount, 0);
    set(state.manualReviewGroupIds, []);
    set(state.ignoredBridgesCount, 0);
    set(state.ignoredMovementsCount, 0);
    set(state.logged, true);
    set(state.matchingAllowed, true);
    set(state.processing, false);
    set(state.trackedEntitiesLoading, false);
    set(state.tracksNothing, false);
    set(state.undecodedCount, 0);
    set(state.unmatchedBridgesCount, 0);
    set(state.unmatchedMovementsCount, 0);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should report no issues when every count is zero', () => {
    const { activeItems, categoryCount, clearedItems, hasItems, issues } = useHistoryEventIssues();

    expect(get(issues)).toHaveLength(7);
    expect(get(activeItems)).toEqual([]);
    expect(get(clearedItems)).toHaveLength(7);
    expect(get(categoryCount)).toBe(0);
    expect(get(hasItems)).toBe(false);
  });

  it('should count categories and not items', () => {
    set(state.unmatchedMovementsCount, 2);
    set(state.unmatchedBridgesCount, 38);
    set(state.internalConflictsCount, 957);
    set(state.undecodedCount, 47);

    const { activeItems, categoryCount, clearedItems, hasItems } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(4);
    expect(get(hasItems)).toBe(true);
    expect(get(activeItems).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
      HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS,
      HISTORY_ISSUE_IDS.UNDECODED,
    ]);
    expect(get(clearedItems).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.NO_TRACKED_ACCOUNTS,
      HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
      HISTORY_ISSUE_IDS.MANUAL_REVIEW_DUPLICATES,
    ]);
  });

  it('should not treat a category as active while its auto-matching is running', () => {
    set(state.unmatchedMovementsCount, 5);
    set(state.autoMatchLoading, true);

    const { activeItems, categoryCount } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(0);
    expect(get(activeItems)).toEqual([]);

    set(state.autoMatchLoading, false);

    expect(get(categoryCount)).toBe(1);
  });

  it('should demote internal conflicts and mark undecoded as informational', () => {
    const { issues } = useHistoryEventIssues();
    const bySeverity = Object.fromEntries(get(issues).map(issue => [issue.id, issue.severity]));

    expect(bySeverity[HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS]).toBe('muted');
    expect(bySeverity[HISTORY_ISSUE_IDS.UNDECODED]).toBe('info');
    expect(bySeverity[HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES]).toBe('warning');
  });

  it('should give bridges their own action label', () => {
    const { issues } = useHistoryEventIssues();
    const bridges = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES);
    const movements = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS);

    expect(bridges?.actionLabel).toBe('transactions.alerts.issues.unmatched_bridges.action');
    expect(movements?.actionLabel).toBe('transactions.alerts.issues.unmatched_movements.action');
  });

  it('should target the matching dialog or duplicate route per issue', () => {
    set(state.autoFixGroupIds, ['group-1', 'group-2']);

    const { issues } = useHistoryEventIssues();
    const bridges = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES);
    const autoFix = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES);

    expect(bridges?.target).toEqual({
      kind: 'dialog',
      options: { type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS },
    });
    expect(autoFix?.target).toEqual({
      groupIds: ['group-1', 'group-2'],
      kind: 'duplicates',
      status: DuplicateHandlingStatus.AUTO_FIX,
    });
  });

  it('should stay pending until a scan lands and while the history syncs', async () => {
    const { checking, refreshAll } = useHistoryEventIssues();

    expect(get(checking)).toBe(true);

    await refreshAll();

    expect(get(checking)).toBe(false);

    set(state.processing, true);

    expect(get(checking)).toBe(true);
  });

  it('should lock the matching rows and keep them out of the attention count without premium', () => {
    set(state.matchingAllowed, false);
    set(state.unmatchedMovementsCount, 2);
    set(state.unmatchedBridgesCount, 38);
    set(state.undecodedCount, 47);

    const { activeItems, categoryCount, lockedItems } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(1);
    expect(get(activeItems).map(issue => issue.id)).toEqual([HISTORY_ISSUE_IDS.UNDECODED]);
    expect(get(lockedItems).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
    ]);
    expect(get(lockedItems)[0].minimumTier).toBe('Basic');
  });

  it('should not lock anything when the matching capability is available', () => {
    set(state.unmatchedBridgesCount, 38);

    const { lockedItems } = useHistoryEventIssues();

    expect(get(lockedItems)).toEqual([]);
  });

  it('should offer the ignored items for review once nothing is left unmatched', () => {
    set(state.ignoredMovementsCount, 4);

    const { activeItems, categoryCount, reviewItems } = useHistoryEventIssues();
    const [movements] = get(reviewItems);

    expect(get(activeItems)).toEqual([]);
    expect(get(categoryCount)).toBe(0);
    expect(movements.id).toBe(HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS);
    expect(movements.count).toBe(4);
    expect(movements.severity).toBe('muted');
    expect(movements.actionLabel).toBe('transactions.alerts.review_ignored');
  });

  it('should prefer the unmatched count over the ignored one', () => {
    set(state.ignoredMovementsCount, 4);
    set(state.unmatchedMovementsCount, 2);

    const { activeItems, reviewItems } = useHistoryEventIssues();

    expect(get(reviewItems)).toEqual([]);
    expect(get(activeItems)[0].count).toBe(2);
  });

  it('should send a cleared duplicates category to the dialog rather than the filtered list', () => {
    const { issues } = useHistoryEventIssues();
    const autoFix = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES);

    expect(autoFix?.checkTarget).toEqual({ kind: 'dialog', options: { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES } });
    expect(autoFix?.target.kind).toBe('duplicates');
  });

  it('should refresh every issue source on re-scan', async () => {
    const { refreshAll } = useHistoryEventIssues();

    await refreshAll();

    expect(state.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    expect(state.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    expect(state.fetchCustomizedEventDuplicates).toHaveBeenCalledOnce();
    expect(state.fetchCounts).toHaveBeenCalledOnce();
    expect(state.fetchUndecodedTransactionsBreakdown).toHaveBeenCalledOnce();
  });

  it('should leave the inbox out entirely when the build does not serve it', async () => {
    set(state.dataIssuesCount, 4);
    const { issues, refreshAll } = useHistoryEventIssues();

    await refreshAll();

    expect(get(issues).map(issue => issue.id)).not.toContain(HISTORY_ISSUE_IDS.DATA_ISSUES);
    expect(get(issues)).toHaveLength(7);
    // The summary costs four requests, so it must not be paid for a hidden row.
    expect(state.refreshDataIssuesSummary).not.toHaveBeenCalled();
  });

  describe('the tracked accounts row', () => {
    it('should raise it first when the user tracks nothing, pointing at the add-account page', () => {
      set(state.tracksNothing, true);

      const { activeItems, categoryCount } = useHistoryEventIssues();
      const [row] = get(activeItems);

      expect(get(categoryCount)).toBe(1);
      expect(row.id).toBe(HISTORY_ISSUE_IDS.NO_TRACKED_ACCOUNTS);
      expect(row.count).toBe(1);
      expect(row.severity).toBe('warning');
      expect(row.target).toEqual({ kind: 'route', to: { name: '/accounts/' } });
    });

    it('should lead the list, since every other count is legitimately zero', () => {
      set(state.tracksNothing, true);
      set(state.undecodedCount, 47);

      const { activeItems } = useHistoryEventIssues();

      expect(get(activeItems).map(issue => issue.id)).toEqual([
        HISTORY_ISSUE_IDS.NO_TRACKED_ACCOUNTS,
        HISTORY_ISSUE_IDS.UNDECODED,
      ]);
    });

    it('should clear it once anything at all is tracked', () => {
      const { activeItems, clearedItems } = useHistoryEventIssues();

      expect(get(activeItems)).toEqual([]);
      expect(get(clearedItems).map(issue => issue.id)).toContain(HISTORY_ISSUE_IDS.NO_TRACKED_ACCOUNTS);
    });

    it('should not raise it while the accounts are still being read', () => {
      set(state.tracksNothing, true);
      set(state.trackedEntitiesLoading, true);

      const { activeItems, categoryCount } = useHistoryEventIssues();

      expect(get(categoryCount)).toBe(0);
      expect(get(activeItems)).toEqual([]);

      set(state.trackedEntitiesLoading, false);

      expect(get(categoryCount)).toBe(1);
    });
  });

  describe('with the inbox enabled', () => {
    beforeEach(() => {
      vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    });

    it('should raise a data issues row that opens the inbox in the pinned rail', () => {
      set(state.dataIssuesCount, 4);
      const { activeItems, issues } = useHistoryEventIssues();
      const row = get(issues).find(issue => issue.id === HISTORY_ISSUE_IDS.DATA_ISSUES);

      expect(get(issues)).toHaveLength(8);
      expect(row?.count).toBe(4);
      expect(row?.severity).toBe('warning');
      expect(row?.target).toEqual({ kind: 'pin', panel: { name: PinnedNames.DATA_ISSUES, props: {} } });
      expect(get(activeItems).map(issue => issue.id)).toContain(HISTORY_ISSUE_IDS.DATA_ISSUES);
    });

    it('should clear the data issues row when nothing is actionable', () => {
      const { activeItems, clearedItems } = useHistoryEventIssues();

      expect(get(activeItems)).toEqual([]);
      expect(get(clearedItems).map(issue => issue.id)).toContain(HISTORY_ISSUE_IDS.DATA_ISSUES);
    });

    it('should refresh the inbox summary alongside the other sources', async () => {
      const { refreshAll } = useHistoryEventIssues();

      await refreshAll();

      expect(state.refreshDataIssuesSummary).toHaveBeenCalledOnce();
    });
  });
});
