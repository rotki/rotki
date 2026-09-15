import type { ComputedRef } from 'vue';
import { useMissingMappingsCount } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-count';
import { type ActionItem, ActionSeverity, type ActionTarget, createActionItem } from '@/modules/core/action-center/types';

interface UseAssetRowsReturn {
  rows: ComputedRef<ActionItem[]>;
  /** Re-reads what the rows count. */
  refresh: () => Promise<void>;
}

/** The asset rows: exchange assets that have no mapping in rotki. */
export function useAssetRows(): UseAssetRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { count, refresh } = useMissingMappingsCount();

  const rows = computed<ActionItem[]>(() => [
    createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.assets.missing_mappings.action'),
      count: get(count),
      description: t('action_center.rows.assets.missing_mappings.description'),
      icon: 'lu-cable',
      id: 'missing-exchange-mappings',
      severity: ActionSeverity.WARNING,
      target: { kind: 'route', to: { name: '/asset-manager/more/missing-mappings/' } },
      title: t('action_center.rows.assets.missing_mappings.title'),
    }),
  ]);

  return { refresh, rows };
}
