import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import {
  describeIncompleteSwap,
  describeMissingCostBasis,
  describeMissingPrice,
  describeUnmatchedExchangeTransfer,
  extractIssueResolution,
  isManuallyConfirmed,
  issueImpactMagnitude,
  sortIssuesByImpact,
} from '@/modules/history/data-issues/pnl-transforms';
import { relatedEventRoute } from '@/modules/history/data-issues/transforms';

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    eventIdentifier: 42,
    groupIdentifier: 'grp-1',
    id: 1,
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

describe('pnl data-issues transforms', () => {
  it('should describe a missing price issue with quote asset and amount', () => {
    const result = describeMissingPrice(createIssue({
      asset: 'ETH',
      kind: IssueKind.MISSING_PRICE,
      payload: { amount: '2.5', direction: 'spend', eventIdentifier: 10, groupIdentifier: 'g-1', toAsset: 'USD' },
    }));

    expect(result?.messageKey).toBe('data_issues.description.missing_price');
    expect(result?.shortMessageKey).toBe('data_issues.description_short.missing_price');
    expect(result?.amounts.amount?.toString()).toBe('2.5');
    expect(result?.toAsset).toBe('USD');
    expect(result?.eventIdentifier).toBe(10);
  });

  it('should describe a missing cost basis issue with covered, requested, and uncovered amounts', () => {
    const result = describeMissingCostBasis(createIssue({
      asset: 'BTC',
      kind: IssueKind.MISSING_COST_BASIS,
      payload: {
        coveredAmount: '1.25',
        eventIdentifier: 20,
        fallbackBasis: '0',
        groupIdentifier: 'g-2',
        requestedAmount: '3',
        uncoveredAmount: '1.75',
      },
    }));

    expect(result?.messageKey).toBe('data_issues.description.missing_cost_basis');
    expect(result?.amounts.covered?.toString()).toBe('1.25');
    expect(result?.amounts.requested?.toString()).toBe('3');
    expect(result?.amounts.uncovered?.toString()).toBe('1.75');
    expect(result?.eventIdentifier).toBe(20);
  });

  it.each([
    ['ignored_asset', 'data_issues.description.incomplete_swap_ignored_asset'],
    ['ignored_action', 'data_issues.description.incomplete_swap_ignored_action'],
    ['missing_counterpart_leg', 'data_issues.description.incomplete_swap_missing_leg'],
  ] as const)('should describe incomplete swap for reason %s', (reason, expectedKey) => {
    const result = describeIncompleteSwap(createIssue({
      kind: IssueKind.INCOMPLETE_SWAP,
      payload: {
        eventIdentifier: 30,
        eventIdentifiers: [30],
        excludedAssets: ['SPAM'],
        groupIdentifier: 'g-3',
        missingOrExcludedReason: reason,
        presentLegs: [{ amount: '1', asset: 'ETH', eventIdentifier: 30, subtype: 'receive' }],
      },
    }));

    expect(result?.messageKey).toBe(expectedKey);
    expect(result?.asset).toBe('SPAM');
    expect(result?.eventIdentifier).toBe(30);
  });

  it.each([
    ['spend', 'data_issues.description.unmatched_exchange_transfer_spend'],
    ['receive', 'data_issues.description.unmatched_exchange_transfer_receive'],
  ] as const)('should describe unmatched exchange transfer for subtype %s', (subtype, expectedKey) => {
    const result = describeUnmatchedExchangeTransfer(createIssue({
      kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
      payload: { amount: '500', eventIdentifier: 40, groupIdentifier: 'g-4', subtype },
    }));

    expect(result?.messageKey).toBe(expectedKey);
    expect(result?.amounts.amount?.toString()).toBe('500');
  });

  it('should deep-link unmatched exchange transfers to the asset movement matching dialog', () => {
    expect(relatedEventRoute(IssueKind.UNMATCHED_EXCHANGE_TRANSFER, 40, 'g-4', 'USDC')).toStrictEqual({
      name: '/history/events/',
      query: { openMatchAssetMovementsDialog: 'true' },
    });
  });

  it('should detect manually confirmed issues only when resolved with payload.resolution.manual === true', () => {
    const confirmed = createIssue({
      payload: { resolution: { disposition: 'confirm_zero_basis', manual: true, note: 'mined' } },
      state: IssueState.RESOLVED,
    });
    const autoResolved = createIssue({ payload: {}, state: IssueState.RESOLVED });
    const stillOpen = createIssue({
      payload: { resolution: { manual: true } },
      state: IssueState.OPEN,
    });

    expect(isManuallyConfirmed(confirmed)).toBe(true);
    expect(extractIssueResolution(confirmed)?.disposition).toBe('confirm_zero_basis');
    expect(isManuallyConfirmed(autoResolved)).toBe(false);
    expect(isManuallyConfirmed(stillOpen)).toBe(false);
  });

  it('should sort issues by quantitative impact descending and break ties by timestamp descending', () => {
    const smallNew = createIssue({
      id: 1,
      kind: IssueKind.MISSING_COST_BASIS,
      payload: { coveredAmount: '0', eventIdentifier: 1, fallbackBasis: '0', groupIdentifier: 'g', requestedAmount: '1', uncoveredAmount: '1' },
      tsEnd: 3000,
    });
    const largeOld = createIssue({
      id: 2,
      kind: IssueKind.MISSING_COST_BASIS,
      payload: { coveredAmount: '0', eventIdentifier: 2, fallbackBasis: '0', groupIdentifier: 'g', requestedAmount: '50', uncoveredAmount: '50' },
      tsEnd: 1000,
    });
    const largeNew = createIssue({
      id: 3,
      kind: IssueKind.MISSING_COST_BASIS,
      payload: { coveredAmount: '0', eventIdentifier: 3, fallbackBasis: '0', groupIdentifier: 'g', requestedAmount: '50', uncoveredAmount: '50' },
      tsEnd: 2000,
    });

    expect(issueImpactMagnitude(largeOld).toString()).toBe('50');
    expect(sortIssuesByImpact([smallNew, largeOld, largeNew]).map(issue => issue.id)).toStrictEqual([3, 2, 1]);
  });
});
