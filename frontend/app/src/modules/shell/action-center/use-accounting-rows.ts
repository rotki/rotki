import type { ComputedRef } from 'vue';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useAccountingRuleConflictsCount } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count';

interface UseAccountingRowsReturn {
  rows: ComputedRef<ActionItem[]>;
  /** Re-reads what the rows count. */
  refresh: () => Promise<void>;
}

const ACCOUNTING_RULES: ActionTarget = { kind: 'route', to: { name: '/settings/accounting/' } };

/**
 * The accounting rows: rules that conflict with their remote version.
 *
 * @remarks
 * The action opens the accounting rules page with its resolve dialog up; the page consumes the
 * request, so a reload lands on the page.
 */
export function useAccountingRows(): UseAccountingRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { count, refresh: recount } = useAccountingRuleConflictsCount();

  async function refresh(): Promise<void> {
    await recount();
  }

  const rows = computed<ActionItem[]>(() => [
    createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.history.accounting_rule_conflicts.action'),
      checkTarget: ACCOUNTING_RULES,
      count: get(count),
      description: t('action_center.rows.history.accounting_rule_conflicts.description'),
      icon: 'lu-scale',
      id: 'accounting-rule-conflicts',
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: { name: '/settings/accounting/', query: { resolveConflicts: 'true' } } },
      title: t('action_center.rows.history.accounting_rule_conflicts.title'),
    }),
  ]);

  return { refresh, rows };
}
