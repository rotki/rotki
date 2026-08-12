import type { Ref } from 'vue';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
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
  confirmDelete: (item: AccountingRuleEntry) => void;
  confirmReset: () => void;
}

/**
 * The destructive and bulk operations on the rules: delete one, reset them all, export, import.
 *
 * Both destructive ones are confirmed first, and each reloads what its change can have touched —
 * deleting a rule cannot create a conflict, resetting every rule can.
 */
export function useAccountingRuleMaintenance(
  options: UseAccountingRuleMaintenanceOptions,
): UseAccountingRuleMaintenanceReturn {
  const { refetch, refresh } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
  const { setMessage } = useMessageStore();
  const { useIsActive } = useTaskCenter();
  const { exportJSON, resetToDefaults } = useAccountingSettings();
  const { deleteAccountingRule } = useAccountingApi();

  const modelImportDialogOpen = shallowRef<boolean>(false);

  async function deleteRule(item: AccountingRuleEntry): Promise<void> {
    try {
      const success = await deleteAccountingRule(item.identifier);
      if (success)
        await refetch();
    }
    catch {
      setMessage({
        description: t('accounting_settings.rule.delete_error'),
      });
    }
  }

  async function resetRulesToDefaults(): Promise<void> {
    const result = await resetToDefaults();
    if (result?.success)
      await refresh();
  }

  function confirmDelete(item: AccountingRuleEntry): void {
    show({
      message: t('accounting_settings.rule.confirm_delete'),
      title: t('accounting_settings.rule.delete'),
    }, async () => deleteRule(item));
  }

  function confirmReset(): void {
    show({
      message: t('accounting_settings.rule.confirm_reset'),
      title: t('accounting_settings.rule.reset'),
    }, resetRulesToDefaults);
  }

  return {
    confirmDelete,
    confirmReset,
    exportFileLoading: useIsActive(ActivityKind.ACCOUNTING_RULES, ActivityPart.EXPORT),
    exportJSON,
    importFileLoading: useIsActive(ActivityKind.ACCOUNTING_RULES, ActivityPart.IMPORT),
    modelImportDialogOpen,
    resetLoading: useIsActive(ActivityKind.ACCOUNTING_RULES, ActivityPart.RESET),
  };
}
