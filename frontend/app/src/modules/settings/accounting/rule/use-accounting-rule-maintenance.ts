import type { Ref } from 'vue';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import {
  accountingRulesExportActivity,
  accountingRulesImportActivity,
  accountingRulesResetActivity,
} from '@/modules/settings/accounting/accounting-rules.activity';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAccountingRuleMaintenanceOptions {
  /** Reloads the table alone, after a change that cannot have created a conflict. */
  refetch: () => Promise<void>;
  /** Reloads the table and re-counts conflicts, after a change that can. */
  refresh: () => Promise<void>;
}

interface UseAccountingRuleMaintenanceReturn {
  exportFileLoading: Readonly<Ref<boolean>>;
  importFileLoading: Readonly<Ref<boolean>>;
  resetLoading: Readonly<Ref<boolean>>;
  modelImportDialogOpen: Ref<boolean>;
  exportJSON: () => Promise<void>;
  /** What a row's delete button asks before deleting its rule. */
  deleteConfirm: (item: AccountingRuleEntry) => RowDeleteQuestion;
  /** Deletes a rule the user already confirmed. */
  deleteRule: (item: AccountingRuleEntry) => Promise<void>;
  /** Why the last delete failed, named above the table. */
  deleteFailure: Readonly<Ref<NamedFailure | undefined>>;
  /** Resets every rule to the defaults, which the header menu has already confirmed. */
  resetRules: () => Promise<void>;
}

/**
 * The destructive and bulk operations on the rules: delete one, reset them all, export, import.
 *
 * @remarks
 * Both destructive ones are confirmed by their trigger first. Each reloads what its change can
 * have touched: deleting a rule cannot create a conflict, resetting every rule can.
 */
export function useAccountingRuleMaintenance(
  options: UseAccountingRuleMaintenanceOptions,
): UseAccountingRuleMaintenanceReturn {
  const { refetch, refresh } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { useIsActive } = useTaskCenter();
  const { exportJSON, resetToDefaults } = useAccountingSettings();
  const { deleteAccountingRule } = useAccountingApi();

  const modelImportDialogOpen = shallowRef<boolean>(false);

  const deleteConfirm = (): RowDeleteQuestion => ({
    message: t('accounting_settings.rule.confirm_delete'),
    title: t('accounting_settings.rule.delete'),
  });

  const { deleteRow: deleteRule, failure: deleteFailure } = useTableRowDeletion<AccountingRuleEntry>({
    deleteItem: async item => deleteAccountingRule(item.identifier),
    failureTitle: () => t('accounting_settings.rule.delete_error'),
    onDeleted: refetch,
  });

  async function resetRules(): Promise<void> {
    const result = await resetToDefaults();
    if (result?.success)
      await refresh();
  }

  return {
    deleteConfirm,
    deleteFailure,
    deleteRule,
    exportFileLoading: useIsActive(accountingRulesExportActivity.kind, ...accountingRulesExportActivity.partsOf()),
    exportJSON,
    importFileLoading: useIsActive(accountingRulesImportActivity.kind, ...accountingRulesImportActivity.partsOf()),
    modelImportDialogOpen,
    resetLoading: useIsActive(accountingRulesResetActivity.kind, ...accountingRulesResetActivity.partsOf()),
    resetRules,
  };
}
