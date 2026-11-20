import { describe, expect, it } from 'vitest';
import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

describe('useDataIssuesFormat', () => {
  it.each([
    [IssueState.OPEN, 'data_issues.state.open'],
    [IssueState.AUTO_REMEDIATING, 'data_issues.state.auto_remediating'],
    [IssueState.UNRESOLVED, 'data_issues.state.unresolved'],
    [IssueState.RESOLVED, 'data_issues.state.resolved'],
    [IssueState.DISMISSED, 'data_issues.state.dismissed'],
  ])('should return the translated label for state %s', (state, expectedKey) => {
    const { stateLabel } = useDataIssuesFormat();
    expect(stateLabel(state)).toBe(expectedKey);
  });

  it.each([
    [IssueKind.NEGATIVE_BALANCE, 'data_issues.kind.negative_balance'],
    [IssueKind.INVALID_EVENT_AMOUNT, 'data_issues.kind.invalid_event_amount'],
    [IssueKind.CURRENT_BALANCE_MISMATCH, 'data_issues.kind.current_balance_mismatch'],
    [IssueKind.REBASING_TOKEN, 'data_issues.kind.rebasing_token'],
    [IssueKind.UNMATCHED_BRIDGE, 'data_issues.kind.unmatched_bridge'],
  ])('should return the translated label for kind %s', (kind, expectedKey) => {
    const { kindLabel } = useDataIssuesFormat();
    expect(kindLabel(kind)).toBe(expectedKey);
  });
});
