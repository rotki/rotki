import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { describeIssue, humanizeStrategy, toTimelineItems } from '@/modules/history/data-issues/transforms';

function identityTranslator(key: string, params?: Record<string, unknown>): string {
  return params ? `${key}:${JSON.stringify(params)}` : key;
}

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
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
    it('should describe a negative balance issue and expose the event identifier', () => {
      const issue = createIssue({
        kind: IssueKind.NEGATIVE_BALANCE,
        payload: {
          derivedBalanceBeforeEvent: '0',
          eventIdentifier: 42,
          inMemoryNegativeAmount: '-1',
        },
      });

      const result = describeIssue(issue, identityTranslator);

      expect(result.eventIdentifier).toBe(42);
      expect(result.summary).toContain('data_issues.description.negative_balance');
      // amount is shown as its absolute value.
      expect(result.summary).toContain('"amount":"1"');
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

      const result = describeIssue(issue, identityTranslator);

      expect(result.eventIdentifier).toBe(7);
      expect(result.summary).toContain('data_issues.description.current_balance_mismatch');
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

      expect(describeIssue(issue, identityTranslator).eventIdentifier).toBeUndefined();
    });

    it('should fall back to an unknown description when the payload does not match the kind', () => {
      const issue = createIssue({ kind: IssueKind.NEGATIVE_BALANCE, payload: { garbage: true } });

      const result = describeIssue(issue, identityTranslator);

      expect(result.summary).toBe('data_issues.description.unknown');
      expect(result.eventIdentifier).toBeUndefined();
    });
  });

  describe('toTimelineItems', () => {
    it('should order attempts oldest-first by timestamp', () => {
      const issue = createIssue({
        autoRemediationAttempts: [
          { strategy: 'second', success: true, timestamp: 200 },
          { strategy: 'first', success: false, timestamp: 100 },
        ],
      });

      const items = toTimelineItems(issue);

      expect(items.map(item => item.strategy)).toEqual(['first', 'second']);
    });

    it('should return an empty array when there are no attempts', () => {
      expect(toTimelineItems(createIssue())).toEqual([]);
    });
  });
});
