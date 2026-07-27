import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { HISTORY_ISSUE_IDS, type useHistoryEventIssues as UseHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';

// Declared at module scope (not `vi.hoisted`): the mock factories below only
// dereference `state` from inside their inner arrows, which run once the tests do.
const state = {
  autoFixCount: ref(0),
  autoFixGroupIds: ref<string[]>([]),
  autoMatchLoading: ref(false),
  bridgeAutoMatchLoading: ref(false),
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
  refreshUnmatchedAssetMovements: vi.fn<() => Promise<void>>(),
  refreshUnmatchedBridgeTransactions: vi.fn<() => Promise<void>>(),
  undecodedCount: ref(0),
  unmatchedBridgesCount: ref(0),
  unmatchedMovementsCount: ref(0),
};

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

vi.mock('@/modules/history/events/tx/use-undecoded-transactions-count', () => ({
  useUndecodedTransactionsCount: (): object => ({
    fetchUndecodedTransactionsBreakdown: state.fetchUndecodedTransactionsBreakdown,
    undecodedCount: state.undecodedCount,
  }),
}));

// `scanned` is module state shared by the trigger and the panel, so each test
// loads a fresh copy instead of inheriting whether a previous one scanned.
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
    set(state.internalConflictsCount, 0);
    set(state.manualReviewCount, 0);
    set(state.manualReviewGroupIds, []);
    set(state.ignoredBridgesCount, 0);
    set(state.ignoredMovementsCount, 0);
    set(state.logged, true);
    set(state.matchingAllowed, true);
    set(state.processing, false);
    set(state.undecodedCount, 0);
    set(state.unmatchedBridgesCount, 0);
    set(state.unmatchedMovementsCount, 0);
  });

  it('should report no issues when every count is zero', () => {
    const { activeIssues, categoryCount, clearedIssues, hasIssues, issues } = useHistoryEventIssues();

    expect(get(issues)).toHaveLength(6);
    expect(get(activeIssues)).toEqual([]);
    expect(get(clearedIssues)).toHaveLength(6);
    expect(get(categoryCount)).toBe(0);
    expect(get(hasIssues)).toBe(false);
  });

  it('should count categories and not items', () => {
    set(state.unmatchedMovementsCount, 2);
    set(state.unmatchedBridgesCount, 38);
    set(state.internalConflictsCount, 957);
    set(state.undecodedCount, 47);

    const { activeIssues, categoryCount, clearedIssues, hasIssues } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(4);
    expect(get(hasIssues)).toBe(true);
    expect(get(activeIssues).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
      HISTORY_ISSUE_IDS.INTERNAL_CONFLICTS,
      HISTORY_ISSUE_IDS.UNDECODED,
    ]);
    expect(get(clearedIssues).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.AUTO_FIX_DUPLICATES,
      HISTORY_ISSUE_IDS.MANUAL_REVIEW_DUPLICATES,
    ]);
  });

  it('should not treat a category as active while its auto-matching is running', () => {
    set(state.unmatchedMovementsCount, 5);
    set(state.autoMatchLoading, true);

    const { activeIssues, categoryCount } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(0);
    expect(get(activeIssues)).toEqual([]);

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

    const { activeIssues, categoryCount, lockedIssues } = useHistoryEventIssues();

    expect(get(categoryCount)).toBe(1);
    expect(get(activeIssues).map(issue => issue.id)).toEqual([HISTORY_ISSUE_IDS.UNDECODED]);
    expect(get(lockedIssues).map(issue => issue.id)).toEqual([
      HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS,
      HISTORY_ISSUE_IDS.UNMATCHED_BRIDGES,
    ]);
    expect(get(lockedIssues)[0].minimumTier).toBe('Basic');
  });

  it('should not lock anything when the matching capability is available', () => {
    set(state.unmatchedBridgesCount, 38);

    const { lockedIssues } = useHistoryEventIssues();

    expect(get(lockedIssues)).toEqual([]);
  });

  it('should offer the ignored items for review once nothing is left unmatched', () => {
    set(state.ignoredMovementsCount, 4);

    const { activeIssues, categoryCount, reviewIssues } = useHistoryEventIssues();
    const [movements] = get(reviewIssues);

    expect(get(activeIssues)).toEqual([]);
    expect(get(categoryCount)).toBe(0);
    expect(movements.id).toBe(HISTORY_ISSUE_IDS.UNMATCHED_MOVEMENTS);
    expect(movements.count).toBe(4);
    expect(movements.severity).toBe('muted');
    expect(movements.actionLabel).toBe('transactions.alerts.review_ignored');
  });

  it('should prefer the unmatched count over the ignored one', () => {
    set(state.ignoredMovementsCount, 4);
    set(state.unmatchedMovementsCount, 2);

    const { activeIssues, reviewIssues } = useHistoryEventIssues();

    expect(get(reviewIssues)).toEqual([]);
    expect(get(activeIssues)[0].count).toBe(2);
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
});
