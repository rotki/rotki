import type { StateHandler } from '../interfaces';
import type { AccountingRuleConflictData } from '../types/business-types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useAccountingRuleConflictsCount } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count';

/**
 * Re-reads the conflicting accounting rules, which the action center counts.
 *
 * @remarks
 * Creates no notification: the count stays in the center until the conflicts are resolved. The
 * message's own count is not used, since a re-read also covers conflicts resolved since.
 */
export function createAccountingRuleConflictHandler(): StateHandler<AccountingRuleConflictData> {
  const { refresh } = useAccountingRuleConflictsCount();

  return createStateHandler<AccountingRuleConflictData>(async () => {
    await refresh();
  });
}
