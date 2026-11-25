import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { get, set } from '@vueuse/core';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssueRemediationActions } from '@/modules/history/data-issues/use-data-issue-remediation-actions';

const { matchingAllowed, spies } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    matchingAllowed: ref<boolean>(true),
    spies: {
      ignoreActions: vi.fn(),
      ignoreAsset: vi.fn(),
      matchAssetMovements: vi.fn(),
      push: vi.fn(),
      resolveManually: vi.fn(),
      retry: vi.fn(),
      unignoreAsset: vi.fn(),
    },
  };
});

vi.mock('@/modules/premium/use-feature-access', () => ({
  PremiumFeature: { ASSET_MOVEMENT_MATCHING: 'asset_movement_matching' },
  useFeatureAccess: (): { allowed: typeof matchingAllowed } => ({ allowed: matchingAllowed }),
}));

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push: spies.push }),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): Record<string, unknown> => ({
    ignoreAsset: spies.ignoreAsset,
    unignoreAsset: spies.unignoreAsset,
  }),
}));

vi.mock('@/modules/history/api/use-history-ignoring-api', () => ({
  useHistoryIgnoringApi: (): Record<string, unknown> => ({
    ignoreActions: spies.ignoreActions,
  }),
}));

vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): Record<string, unknown> => ({
    matchAssetMovements: spies.matchAssetMovements,
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    resolveManually: spies.resolveManually,
    retry: spies.retry,
  }),
}));

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    eventIdentifier: 42,
    groupIdentifier: 'grp-1',
    id: 7,
    kind: IssueKind.MISSING_PRICE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    suggestedActions: [],
    tsEnd: 1710000000000,
    tsStart: 1710000000000,
    ...overrides,
  };
}

describe('useDataIssueRemediationActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(matchingAllowed, true);
  });

  it('should open the manual price dialog for set_manual_price without calling reload yet', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const { hasModalOpen, modelPriceUpdate, runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'set_manual_price', issue: createIssue({ asset: 'ETH', tsEnd: 1710000000000 }) });

    expect(get(modelPriceUpdate)).toStrictEqual({ asset: 'ETH', timestamp: 1710000000000 });
    expect(get(hasModalOpen)).toBe(true);
    expect(reload).not.toHaveBeenCalled();
  });

  it('should confirm zero basis with disposition confirm_zero_basis and reload on success', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.resolveManually.mockResolvedValue(ok(createIssue({ state: IssueState.RESOLVED })));
    const { runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'confirm_zero_basis', issue: createIssue({ id: 15, kind: IssueKind.MISSING_COST_BASIS }) });

    expect(spies.resolveManually).toHaveBeenCalledWith(15, undefined, 'confirm_zero_basis');
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should dismiss an incomplete swap as standalone with disposition dismiss_as_standalone', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.resolveManually.mockResolvedValue(ok(createIssue({ state: IssueState.RESOLVED })));
    const { runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'dismiss_as_standalone', issue: createIssue({ id: 22, kind: IssueKind.INCOMPLETE_SWAP }) });

    expect(spies.resolveManually).toHaveBeenCalledWith(22, undefined, 'dismiss_as_standalone');
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should unignore excluded assets on an incomplete swap and reload', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.unignoreAsset.mockResolvedValue({ success: true });
    const { runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({
      action: 'unignore_asset',
      issue: createIssue({
        kind: IssueKind.INCOMPLETE_SWAP,
        payload: {
          eventIdentifier: 42,
          eventIdentifiers: [42],
          excludedAssets: ['DUST'],
          groupIdentifier: 'grp-1',
          missingOrExcludedReason: 'ignored_asset',
          presentLegs: [],
        },
      }),
    });

    expect(spies.unignoreAsset).toHaveBeenCalledWith(['DUST']);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should ignore the event group via useHistoryIgnoringApi', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.ignoreActions.mockResolvedValue(true);
    const { runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'ignore_group', issue: createIssue({ groupIdentifier: 'swap-grp-9' }) });

    expect(spies.ignoreActions).toHaveBeenCalledWith({ data: ['swap-grp-9'] });
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should resolve an unmatched exchange transfer as external and report errors without reloading', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.matchAssetMovements.mockResolvedValueOnce(true);
    const { actionFailure, runRemediation } = useDataIssueRemediationActions(reload);
    const issue = createIssue({
      eventIdentifier: 88,
      kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
    });

    await runRemediation({ action: 'resolve_as_external', issue });
    expect(spies.matchAssetMovements).toHaveBeenCalledWith(88, undefined, true);
    expect(reload).toHaveBeenCalledOnce();

    reload.mockClear();
    spies.matchAssetMovements.mockRejectedValueOnce(new Error('Premium required'));
    await runRemediation({ action: 'resolve_as_external', issue });

    expect(get(actionFailure)?.title).toBe('data_issues.inline_actions.error.resolve_as_external');
    expect(reload).not.toHaveBeenCalled();
  });

  it('should report failure and skip reload when auto_match_exchange_transfer fails', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    spies.retry.mockResolvedValue(err({ cause: new Error('conflict'), message: 'conflict', type: 'conflict' }));
    const { actionFailure, runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'auto_match_exchange_transfer', issue: createIssue({ id: 5, kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER }) });

    expect(spies.retry).toHaveBeenCalledWith(5);
    expect(get(actionFailure)?.title).toBe('data_issues.action.retry.error');
    expect(reload).not.toHaveBeenCalled();
  });

  it('should open the add-event dialog for add_acquisition and matching dialog for match_transfer', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const { modelEventForm, modelMatchingOpen, runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({ action: 'add_acquisition', issue: createIssue({ kind: IssueKind.MISSING_COST_BASIS }) });
    expect(get(modelEventForm)).toStrictEqual({ nextSequenceId: '0', type: 'add' });

    await runRemediation({ action: 'match_transfer', issue: createIssue({ kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER }) });
    expect(get(modelMatchingOpen)).toBe(true);
  });

  it('should not call matchAssetMovements for resolve_as_external when premium access is unavailable', async () => {
    set(matchingAllowed, false);
    const reload = vi.fn().mockResolvedValue(undefined);
    const { runRemediation } = useDataIssueRemediationActions(reload);

    await runRemediation({
      action: 'resolve_as_external',
      issue: createIssue({ eventIdentifier: 88, kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER }),
    });

    expect(spies.matchAssetMovements).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
  });

  it('should keep hasModalOpen true while a nested sub-modal is open', () => {
    const { hasModalOpen, modelSubModalOpen } = useDataIssueRemediationActions(vi.fn());

    expect(get(hasModalOpen)).toBe(false);
    set(modelSubModalOpen, true);
    expect(get(hasModalOpen)).toBe(true);
  });
});
