import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { describeIssue, humanizeStrategy, relatedEventRoute, toTimelineItems } from '@/modules/history/data-issues/transforms';

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

describe('data-issues transforms', () => {
  describe('humanizeStrategy', () => {
    it('should turn a snake_case strategy into a readable label', () => {
      expect(humanizeStrategy('reprocess_event')).toBe('Reprocess event');
    });

    it('should leave an empty string untouched', () => {
      expect(humanizeStrategy('')).toBe('');
    });
  });

  describe('describeIssue', () => {
    it('should describe a negative balance issue, keeping the amount signed, and expose the event identifier', () => {
      const issue = createIssue({
        asset: 'ETH',
        kind: IssueKind.NEGATIVE_BALANCE,
        payload: {
          derivedBalanceBeforeEvent: '0',
          eventIdentifier: 42,
          inMemoryNegativeAmount: '-1',
        },
      });

      const result = describeIssue(issue);

      expect(result.messageKey).toBe('data_issues.description.negative_balance');
      expect(result.shortMessageKey).toBe('data_issues.description_short.negative_balance');
      expect(result.eventIdentifier).toBe(42);
      expect(result.asset).toBe('ETH');
      expect(result.amounts.amount?.toString()).toBe('-1');
      expect(result.amounts.before?.toString()).toBe('0');
    });

    it('should describe a balance mismatch and link to the latest event when present', () => {
      const issue = createIssue({
        kind: IssueKind.CURRENT_BALANCE_MISMATCH,
        payload: {
          delta: '5',
          derivedBalance: '10',
          latestEventIdentifier: 7,
          observedBalance: '15',
          queriedAtTs: 1710000000,
        },
      });

      const result = describeIssue(issue);

      expect(result.messageKey).toBe('data_issues.description.current_balance_mismatch');
      expect(result.shortMessageKey).toBe('data_issues.description_short.current_balance_mismatch');
      expect(result.eventIdentifier).toBe(7);
      expect(result.amounts.delta?.toString()).toBe('5');
    });

    it('should leave the event identifier undefined when the mismatch has no latest event', () => {
      const issue = createIssue({
        kind: IssueKind.CURRENT_BALANCE_MISMATCH,
        payload: {
          delta: '5',
          derivedBalance: '10',
          latestEventIdentifier: null,
          observedBalance: '15',
          queriedAtTs: 1710000000,
        },
      });

      expect(describeIssue(issue).eventIdentifier).toBeUndefined();
    });

    it.each([
      [
        'archive_node_unavailable',
        'data_issues.description.rebasing_token_archive_node_unavailable',
        'data_issues.description_short.rebasing_token_archive_node_unavailable',
      ],
      [
        'historical_balance_query_failed',
        'data_issues.description.rebasing_token_historical_balance_query_failed',
        'data_issues.description_short.rebasing_token_historical_balance_query_failed',
      ],
      [
        'missing_transaction',
        'data_issues.description.rebasing_token_missing_transaction',
        'data_issues.description_short.rebasing_token_missing_transaction',
      ],
      [
        'unsupported_bucket',
        'data_issues.description.rebasing_token_unsupported_bucket',
        'data_issues.description_short.rebasing_token_unsupported_bucket',
      ],
    ])('should describe the rebasing-token reason %s', (reason, messageKey, shortMessageKey) => {
      const issue = createIssue({
        asset: 'stETH',
        kind: IssueKind.REBASING_TOKEN,
        payload: {
          blockNumber: 123,
          eventIdentifier: 9,
          reason,
        },
      });

      const result = describeIssue(issue);

      expect(result.messageKey).toBe(messageKey);
      expect(result.shortMessageKey).toBe(shortMessageKey);
      expect(result.eventIdentifier).toBe(9);
      expect(result.asset).toBe('stETH');
    });

    it('should describe an unmatched bridge leg with a direction-specific message', () => {
      const issue = createIssue({
        kind: IssueKind.UNMATCHED_BRIDGE,
        payload: {
          bridge: { toAddress: '0xdef', toChain: 'optimism' },
          counterparty: 'hop',
          direction: 'deposit',
          eventIdentifier: 12,
          groupIdentifier: '0xabc',
        },
      });

      const result = describeIssue(issue);

      expect(result.messageKey).toBe('data_issues.description.unmatched_bridge_deposit');
      expect(result.shortMessageKey).toBe('data_issues.description_short.unmatched_bridge_deposit');
      expect(result.eventIdentifier).toBe(12);
      expect(result.asset).toBe('ETH');
    });

    it('should describe an unmatched bridge withdrawal with the withdrawal message', () => {
      const issue = createIssue({
        kind: IssueKind.UNMATCHED_BRIDGE,
        payload: {
          direction: 'withdrawal',
          eventIdentifier: 13,
          groupIdentifier: '0xabc',
        },
      });

      const withdrawal = describeIssue(issue);
      expect(withdrawal.messageKey).toBe('data_issues.description.unmatched_bridge_withdrawal');
      expect(withdrawal.shortMessageKey).toBe('data_issues.description_short.unmatched_bridge_withdrawal');
    });

    it('should fall back to an unknown description when the payload does not match the kind', () => {
      const issue = createIssue({ kind: IssueKind.NEGATIVE_BALANCE, payload: { garbage: true } });

      const result = describeIssue(issue);

      expect(result.messageKey).toBe('data_issues.description.unknown');
      expect(result.shortMessageKey).toBe('data_issues.description_short.unknown');
      expect(result.eventIdentifier).toBeUndefined();
      expect(result.amounts).toEqual({});
    });
  });

  describe('relatedEventRoute', () => {
    it('should deep-link a negative balance to its highlighted event', () => {
      expect(relatedEventRoute(IssueKind.NEGATIVE_BALANCE, 42)).toEqual({
        name: '/history/events/',
        query: { highlightedNegativeBalanceEvent: '42' },
      });
    });

    it('should also pass the group identifier so the events view can page to the event', () => {
      expect(relatedEventRoute(IssueKind.NEGATIVE_BALANCE, 42, '0xabc')).toEqual({
        name: '/history/events/',
        query: { highlightedNegativeBalanceEvent: '42', targetGroupIdentifier: '0xabc' },
      });
    });

    it('should deep-link a rebasing issue to its highlighted event', () => {
      expect(relatedEventRoute(IssueKind.REBASING_TOKEN, 9, '0xdef', 'stETH')).toEqual({
        name: '/history/events/',
        query: {
          asset: 'stETH',
          highlightedNegativeBalanceEvent: '9',
          targetGroupIdentifier: '0xdef',
        },
      });
    });

    it('should link a non negative-balance kind to the events page without a highlight', () => {
      expect(relatedEventRoute(IssueKind.CURRENT_BALANCE_MISMATCH, 7)).toEqual({
        name: '/history/events/',
      });
    });

    it('should also filter by asset when the issue carries one', () => {
      expect(relatedEventRoute(IssueKind.NEGATIVE_BALANCE, 42, '0xabc', 'ETH')).toEqual({
        name: '/history/events/',
        query: { asset: 'ETH', highlightedNegativeBalanceEvent: '42', targetGroupIdentifier: '0xabc' },
      });
    });

    it('should filter a non negative-balance kind by asset alone', () => {
      expect(relatedEventRoute(IssueKind.CURRENT_BALANCE_MISMATCH, 7, undefined, 'BTC')).toEqual({
        name: '/history/events/',
        query: { asset: 'BTC' },
      });
    });

    it('should return undefined when there is no event identifier', () => {
      expect(relatedEventRoute(IssueKind.NEGATIVE_BALANCE, undefined)).toBeUndefined();
    });

    it('should deep-link an unmatched bridge issue to the bridge match dialog', () => {
      expect(relatedEventRoute(IssueKind.UNMATCHED_BRIDGE, 12, '0xabc', 'ETH')).toEqual({
        name: '/history/events/',
        query: { openMatchBridgesDialog: 'true' },
      });
    });
  });

  describe('toTimelineItems', () => {
    it('should order attempts oldest-first by timestamp', () => {
      const issue = createIssue({
        autoRemediationAttempts: [
          {
            changedTransactionCount: 1,
            customizedTransactionCount: 2,
            result: 'redecoding_would_change_balance',
            strategy: 'second',
            success: true,
            timestamp: 200,
          },
          { strategy: 'first', success: false, timestamp: 100 },
        ],
      });

      const items = toTimelineItems(issue);

      expect(items.map(item => item.strategy)).toEqual(['first', 'second']);
      expect(items[1]).toMatchObject({
        changedTransactionCount: 1,
        customizedTransactionCount: 2,
        result: 'redecoding_would_change_balance',
      });
    });

    it('should return an empty array when there are no attempts', () => {
      expect(toTimelineItems(createIssue())).toEqual([]);
    });
  });
});
