import { useI18n } from 'vue-i18n';
import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';

interface UseDataIssuesFormatReturn {
  dispositionLabel: (disposition: string) => string | undefined;
  stateLabel: (state: IssueState) => string;
  kindLabel: (kind: IssueKind) => string;
}

/**
 * Maps issue enums to translated labels using explicit (non-dynamic) keys, so
 * the i18n linter can statically verify every key is present.
 */
export function useDataIssuesFormat(): UseDataIssuesFormatReturn {
  const { t } = useI18n({ useScope: 'global' });

  const dispositionLabel = (disposition: string): string | undefined => {
    switch (disposition) {
      case 'confirm_zero_basis':
        return t('data_issues.disposition.confirm_zero_basis');
      case 'dismiss_as_standalone':
        return t('data_issues.disposition.dismiss_as_standalone');
      default:
        return undefined;
    }
  };

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
      case IssueKind.INVALID_EVENT_AMOUNT:
        return t('data_issues.kind.invalid_event_amount');
      case IssueKind.CURRENT_BALANCE_MISMATCH:
        return t('data_issues.kind.current_balance_mismatch');
      case IssueKind.REBASING_TOKEN:
        return t('data_issues.kind.rebasing_token');
      case IssueKind.UNMATCHED_BRIDGE:
        return t('data_issues.kind.unmatched_bridge');
      case IssueKind.MISSING_PRICE:
        return t('data_issues.kind.missing_price');
      case IssueKind.MISSING_COST_BASIS:
        return t('data_issues.kind.missing_cost_basis');
      case IssueKind.INCOMPLETE_SWAP:
        return t('data_issues.kind.incomplete_swap');
      case IssueKind.UNMATCHED_EXCHANGE_TRANSFER:
        return t('data_issues.kind.unmatched_exchange_transfer');
    }
  };

  return {
    dispositionLabel,
    kindLabel,
    stateLabel,
  };
}
