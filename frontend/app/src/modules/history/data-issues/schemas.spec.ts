import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import {
  DataIssue,
  DataIssuesCollectionResponse,
  IncompleteSwapPayload,
  InvalidEventAmountPayload,
  MissingCostBasisPayload,
  MissingPricePayload,
  UnmatchedExchangeTransferPayload,
} from '@/modules/history/data-issues/schemas';

/**
 * A comparison as the backend stores it, before parsing.
 *
 * @remarks
 * Parsed output cannot stand in here: `NumericString` turns the amounts into `BigNumber`s, which
 * the same schema then rejects on the way back in, so a fixture built from it fails for a reason
 * that has nothing to do with the field under test.
 */
function wireComparison(txHash: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const event = {
    amount: '2',
    asset: 'ETH',
    balanceEffect: '-2',
    customized: true,
    eventSubtype: null,
    eventType: 'spend',
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    sequenceIndex: 1,
    timestamp: 1710000000000,
    userNotes: 'My edited spend',
  };
  return {
    decodedEvents: [{ ...event, amount: '1', balanceEffect: '-1', customized: false }],
    groupIdentifier: 'group-1',
    savedEvents: [event],
    txHash,
    ...overrides,
  };
}

function parseIssue(attempt: Record<string, unknown>): DataIssue {
  return DataIssue.parse({
    asset: 'ETH',
    autoRemediationAttempts: [attempt],
    createdAt: 1,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: null,
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1,
    tsStart: 1,
  });
}

describe('historical decoding comparisons', () => {
  const intact = `0x${'ab'.repeat(32)}`;
  const incomplete = `0x${'cd'.repeat(32)}`;

  it('should keep the transactions that parse when one snapshot is incomplete', () => {
    const issue = parseIssue({
      strategy: 'redecode_customized_transactions',
      transactions: [
        wireComparison(intact),
        wireComparison(incomplete, { savedEvents: [{ amount: '2', asset: 'ETH', customized: true, eventSubtype: null, eventType: 'spend', location: 'ethereum', locationLabel: null, sequenceIndex: 1, timestamp: 1710000000000 }] }),
      ],
    });

    expect(issue.autoRemediationAttempts[0]?.transactions?.map(comparison => comparison.txHash)).toEqual([intact]);
    expect(issue.id).toBe(1);
  });

  it('should parse a stored comparison the current backend writes', () => {
    const issue = parseIssue({ strategy: 'redecode_customized_transactions', transactions: [wireComparison(intact)] });

    expect(issue.autoRemediationAttempts[0]?.transactions).toHaveLength(1);
    expect(issue.autoRemediationAttempts[0]?.transactions?.[0]?.savedEvents[0]?.amount.toString()).toBe('2');
  });

  it('should keep an attempt that stored no transactions at all', () => {
    const issue = parseIssue({ strategy: 'reprocess_event' });

    expect(issue.autoRemediationAttempts[0]?.transactions).toBeUndefined();
  });
});

describe('invalid event amount schema', () => {
  it('should accept invalid_event_amount entries in a data issues collection response', () => {
    const parsed = DataIssuesCollectionResponse.parse({
      entries: [{
        asset: 'ETH',
        autoRemediationAttempts: [],
        createdAt: 1,
        id: 7,
        kind: IssueKind.INVALID_EVENT_AMOUNT,
        location: 'ethereum',
        locationLabel: '0x0000000000000000000000000000000000000001',
        payload: { amount: '-0.05', eventIdentifier: 42 },
        protocol: null,
        resolvedAt: null,
        severity: IssueSeverity.WARNING,
        state: IssueState.OPEN,
        tsEnd: 1,
        tsStart: 1,
      }],
      entriesFound: 1,
    });

    expect(parsed.entries).toHaveLength(1);
    expect(parsed.entries[0]?.kind).toBe(IssueKind.INVALID_EVENT_AMOUNT);
    expect(parsed.entriesTotal).toBe(1);

    const payload = InvalidEventAmountPayload.parse(parsed.entries[0]?.payload);
    expect(payload.eventIdentifier).toBe(42);
    expect(payload.amount.toString()).toBe('-0.05');
  });
});

describe('pnl data issue schemas', () => {
  it('should parse top-level eventIdentifier and suggestedActions on DataIssue', () => {
    const issue = DataIssue.parse({
      asset: 'ETH',
      autoRemediationAttempts: [],
      createdAt: 100,
      eventIdentifier: 99,
      groupIdentifier: 'grp-99',
      id: 12,
      kind: IssueKind.MISSING_PRICE,
      location: 'ethereum',
      locationLabel: null,
      payload: {
        amount: '1.5',
        direction: 'spend',
        eventIdentifier: 99,
        groupIdentifier: 'grp-99',
        toAsset: 'USD',
      },
      protocol: null,
      resolvedAt: null,
      severity: IssueSeverity.WARNING,
      state: IssueState.OPEN,
      suggestedActions: [{
        action: 'set_manual_price',
        endpoint: 'PUT /api/1/assets/prices/manual',
        params: { fromAsset: 'ETH', toAsset: 'USD' },
        requiresInput: ['price'],
      }],
      tsEnd: 1710000000000,
      tsStart: 1710000000000,
    });

    expect(issue.eventIdentifier).toBe(99);
    expect(issue.suggestedActions).toHaveLength(1);
    expect(issue.suggestedActions[0]?.action).toBe('set_manual_price');

    const payload = MissingPricePayload.parse(issue.payload);
    expect(payload.amount.toString()).toBe('1.5');
    expect(payload.toAsset).toBe('USD');
  });

  it('should parse missing_cost_basis, incomplete_swap, and unmatched_exchange_transfer payloads', () => {
    const costBasis = MissingCostBasisPayload.parse({
      coveredAmount: '1',
      eventIdentifier: 10,
      fallbackBasis: '0',
      groupIdentifier: 'g-10',
      requestedAmount: '3',
      uncoveredAmount: '2',
    });
    expect(costBasis.uncoveredAmount.toString()).toBe('2');

    const swap = IncompleteSwapPayload.parse({
      eventIdentifier: 11,
      eventIdentifiers: [11],
      excludedAssets: ['SPAM'],
      groupIdentifier: 'g-11',
      missingOrExcludedReason: 'ignored_asset',
      presentLegs: [{ amount: '0.5', asset: 'ETH', eventIdentifier: 11, subtype: 'receive' }],
    });
    expect(swap.excludedAssets).toStrictEqual(['SPAM']);
    expect(swap.presentLegs[0]?.amount.toString()).toBe('0.5');

    const transfer = UnmatchedExchangeTransferPayload.parse({
      amount: '4.2',
      eventIdentifier: 12,
      groupIdentifier: 'g-12',
      subtype: 'spend',
      txRef: '0xabc',
    });
    expect(transfer.amount.toString()).toBe('4.2');
    expect(transfer.subtype).toBe('spend');
  });
});
