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
    [IssueKind.MISSING_PRICE, 'data_issues.kind.missing_price'],
    [IssueKind.MISSING_COST_BASIS, 'data_issues.kind.missing_cost_basis'],
    [IssueKind.INCOMPLETE_SWAP, 'data_issues.kind.incomplete_swap'],
    [IssueKind.UNMATCHED_EXCHANGE_TRANSFER, 'data_issues.kind.unmatched_exchange_transfer'],
  ])('should return the translated label for kind %s', (kind, expectedKey) => {
    const { kindLabel } = useDataIssuesFormat();
    expect(kindLabel(kind)).toBe(expectedKey);
  });

  it('should return translated disposition labels and undefined for unknown dispositions', () => {
    const { dispositionLabel } = useDataIssuesFormat();

    expect(dispositionLabel('confirm_zero_basis')).toBe('data_issues.disposition.confirm_zero_basis');
    expect(dispositionLabel('dismiss_as_standalone')).toBe('data_issues.disposition.dismiss_as_standalone');
    expect(dispositionLabel('custom')).toBeUndefined();
  });
});
