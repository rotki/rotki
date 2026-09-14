import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { DataIssue } from '@/modules/history/data-issues/schemas';

describe('historical decoding comparisons', () => {
  it('should preserve the issue when a nested snapshot is incomplete', () => {
    const transaction = createDecodingComparison();
    const issue = DataIssue.parse({
      asset: 'ETH',
      autoRemediationAttempts: [{ strategy: 'redecode_customized_transactions', transactions: [{ ...transaction, savedEvents: [{ ...transaction.savedEvents[0], balanceEffect: undefined }] }] }],
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
    expect(issue.autoRemediationAttempts[0]?.transactions).toBeUndefined();
    expect(issue.id).toBe(1);
  });
});
