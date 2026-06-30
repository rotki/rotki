import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';

interface UseDataIssuesFormatReturn {
  stateLabel: (state: IssueState) => string;
  kindLabel: (kind: IssueKind) => string;
}

/**
 * Maps issue enums to translated labels using explicit (non-dynamic) keys, so
 * the i18n linter can statically verify every key is present.
 */
export function useDataIssuesFormat(): UseDataIssuesFormatReturn {
  const { t } = useI18n({ useScope: 'global' });

  const stateLabel = (state: IssueState): string => {
    switch (state) {
      case IssueState.OPEN:
        return t('data_issues.state.open');
      case IssueState.AUTO_REMEDIATING:
        return t('data_issues.state.auto_remediating');
      case IssueState.UNRESOLVED:
        return t('data_issues.state.unresolved');
      case IssueState.RESOLVED:
        return t('data_issues.state.resolved');
      case IssueState.DISMISSED:
        return t('data_issues.state.dismissed');
    }
  };

  const kindLabel = (kind: IssueKind): string => {
    switch (kind) {
      case IssueKind.NEGATIVE_BALANCE:
        return t('data_issues.kind.negative_balance');
      case IssueKind.CURRENT_BALANCE_MISMATCH:
        return t('data_issues.kind.current_balance_mismatch');
    }
  };

  return {
    kindLabel,
    stateLabel,
  };
}
