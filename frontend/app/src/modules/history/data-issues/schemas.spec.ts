import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { DataIssue } from '@/modules/history/data-issues/schemas';

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
