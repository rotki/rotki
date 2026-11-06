import type { Ref } from 'vue';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { NotificationKind, Severity } from '@rotki/common';
import { assetResetActivity } from '@/modules/assets/assets.activity';
import { useAssets } from '@/modules/assets/use-assets';
import { DialogType } from '@/modules/core/common/dialogs';
import { useConfirm } from '@/modules/core/common/use-confirm';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { isActionable } from '@/modules/core/tasks/task-result';
import { useBackendReload } from '@/modules/shell/app/use-backend-reload';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

export type ResetType = 'soft' | 'hard';

/**
 * The failure that means the reset would delete assets the user added.
 *
 * @remarks
 * Matched on the message because the endpoint reports it as a plain conflict rather than a code.
 */
const UNDELETABLE_ASSETS = 'There are assets that can not';

interface UseRestoreAssetDbReturn {
  /** Whether a reset is running, which is what stops a second one being started. */
  loading: Ref<boolean>;
  /** What the reset button asks before `restoreAssets` runs, the shared-database caveat included. */
  restoreQuestion: (type: ResetType) => ConfirmQuestion;
  /**
   * Resets the assets database, which the button has already confirmed.
   *
   * @remarks
   * Still asks in a dialog when the backend refuses because assets the user added would go, and
   * holds the forced re-login until the user acknowledges the reset.
   */
  restoreAssets: (type: ResetType) => Promise<void>;
}

/**
 * Drives the reset-assets-database action: the question its button asks, the reset itself, and the
 * reload that has to follow a successful one.
 *
 * @returns whether a reset is running, and the way to start one
 */
export function useRestoreAssetDb(): UseRestoreAssetDbReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { notify } = useNotificationDispatcher();
  const { restoreAssetsDatabase } = useAssets();
  const { reload } = useBackendReload();
  const { ask } = useConfirm();
  const { useIsActive } = useTaskCenter();

  const loading = useIsActive(assetResetActivity.kind, ...assetResetActivity.partsOf());

  /** Holds the forced re-login until the user acknowledges the reset, however they close the notice. */
  async function acknowledgeRestore(): Promise<void> {
    await ask({
      message: t('asset_update.restore.success.description'),
      primaryAction: t('common.actions.ok'),
      singleAction: true,
      title: t('asset_update.restore.success.title'),
      type: DialogType.SUCCESS,
    });
    await reload();
  }

  /** The backend refused because assets the user added would go; resets anyway only if they agree. */
  async function confirmDangerousRestore(type: ResetType): Promise<void> {
    const choice = await ask({
      message: t('asset_update.restore.hard_restore_confirmation.message'),
      title: t('asset_update.restore.hard_restore_confirmation.title'),
    });
    if (choice === 'confirm')
      await restoreAssets(type);
  }

  async function restoreAssets(resetType: ResetType): Promise<void> {
    if (get(loading))
      return;

    const outcome = await restoreAssetsDatabase(resetType);

    if (outcome.ok) {
      await acknowledgeRestore();
      return;
    }

    if (!isActionable(outcome.error))
      return;

    const { message } = outcome.error;
    notify({ kind: NotificationKind.RESULT, message, severity: Severity.ERROR, title: t('asset_update.restore.title') });
    if (message.includes(UNDELETABLE_ASSETS))
      await confirmDangerousRestore(resetType);
  }

  /** Carries the shared-database caveat as its own paragraph, shown when it matters: at the reset. */
  function restoreQuestion(type: ResetType): ConfirmQuestion {
    const soft = type === 'soft';
    const message = soft
      ? t('asset_update.restore.delete_confirmation.soft_reset_message')
      : t('asset_update.restore.delete_confirmation.hard_reset_message');
    return {
      confirmLabel: soft ? t('asset_update.restore.soft_reset') : t('asset_update.restore.hard_reset'),
      message: `${message}\n\n${t('asset_update.restore.warning')}`,
      title: t('asset_update.restore.delete_confirmation.title'),
      tone: 'error',
    };
  }

  return {
    loading,
    restoreAssets,
    restoreQuestion,
  };
}
