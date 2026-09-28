import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useGnosisPaySafeMigration } from '@/modules/integrations/gnosis-pay/use-gnosis-pay-safe-migration';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useSuppressOption } from '@/modules/shell/action-center/row-options';

interface UseGnosisPaySafeRowsReturn {
  rows: ComputedRef<ActionItem[]>;
  /** Re-reads what the rows count. */
  refresh: () => Promise<void>;
}

/**
 * The external services page, without the `service` query: that query opens the Gnosis Pay sign-in
 * dialog, which covers the card's own migration banner.
 */
const EXTERNAL_SERVICES: ActionTarget = { kind: 'route', to: { name: '/api-keys/external/' } };

/**
 * The Gnosis Pay Safe row: the Safe the Gnosis Pay migration left untracked.
 *
 * @remarks
 * Adding the Safe runs in place, the way the Gnosis Pay card does it, and the row leaves once the Safe
 * is added. "Do not show again" writes the setting that keeps it from being raised again.
 */
export function useGnosisPaySafeRows(): UseGnosisPaySafeRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { addMissingSafe, adding, checkMigration, untrackedSafe } = useGnosisPaySafeMigration();
  const neverShow = useSetting('gnosisPaySafeMigrationNeverNotify');
  const { updateFrontendSetting } = useSettingsOperations();
  const { suppressOption } = useSuppressOption();

  const add: ActionTarget = { kind: 'run', run: () => startPromise(addMissingSafe()) };

  const rows = computed<ActionItem[]>(() => {
    const safe = get(untrackedSafe);

    return [createActionItem<ActionTarget, string>({
      actionLabel: t('external_services.gnosispay.safe_migration.add_action'),
      checkTarget: EXTERNAL_SERVICES,
      count: safe && !get(neverShow) ? 1 : 0,
      description: safe?.type === 'new'
        ? t('external_services.gnosispay.safe_migration.missing_new', { address: safe.address })
        : t('external_services.gnosispay.safe_migration.missing_old', { address: safe?.address ?? '' }),
      icon: 'lu-shield-plus',
      id: 'gnosis-pay-safe-migration',
      loading: get(adding),
      options: [suppressOption({
        confirmMessage: t('action_center.rows.integrations.gnosis_pay_safe_migration.suppress_confirm.message'),
        confirmTitle: t('action_center.rows.integrations.gnosis_pay_safe_migration.suppress_confirm.title'),
        label: t('action_center.rows.integrations.gnosis_pay_safe_migration.do_not_show_again'),
        suppress: async () => {
          await updateFrontendSetting({ gnosisPaySafeMigrationNeverNotify: true });
        },
      })],
      urgency: ActionUrgency.DECISION,
      target: add,
      title: t('external_services.gnosispay.safe_migration.title'),
    })];
  });

  return { refresh: checkMigration, rows };
}
