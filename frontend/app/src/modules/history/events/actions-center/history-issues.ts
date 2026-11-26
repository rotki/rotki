import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { DialogShowOptions } from '@/modules/history/events/dialog-types';
import { TRACKED_ACCOUNTS_ROW_ID } from '@/modules/accounts/use-tracked-accounts-row';
import { type ActionItem, type ActionItemDefinition, type ActionTarget, createActionItem } from '@/modules/core/action-center/types';

/** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
export const HISTORY_ISSUE_IDS = {
  AUTO_FIX_DUPLICATES: 'auto-fix-duplicates',
  DATA_ISSUES: 'data-issues',
  INTERNAL_CONFLICTS: 'internal-conflicts',
  MANUAL_REVIEW_DUPLICATES: 'manual-review-duplicates',
  NO_TRACKED_ACCOUNTS: TRACKED_ACCOUNTS_ROW_ID,
  UNDECODED: 'undecoded',
  UNMATCHED_BRIDGES: 'unmatched-bridges',
  UNMATCHED_MOVEMENTS: 'unmatched-movements',
} as const;

export type HistoryIssueId = typeof HISTORY_ISSUE_IDS[keyof typeof HISTORY_ISSUE_IDS];

/** The shared targets, plus the two only the history page can resolve. */
export type HistoryIssueTarget =
  | ActionTarget
  | { kind: 'dialog'; options: DialogShowOptions }
  | { kind: 'duplicates'; status: DuplicateHandlingStatus; groupIds: string[] };

export type HistoryEventIssue = ActionItem<HistoryIssueTarget, HistoryIssueId>;

export function createIssue(definition: ActionItemDefinition<HistoryIssueTarget, HistoryIssueId>): HistoryEventIssue {
  return createActionItem(definition);
}
