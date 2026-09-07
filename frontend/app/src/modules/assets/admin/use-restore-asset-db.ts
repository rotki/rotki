import type { Ref } from 'vue';
import { Severity } from '@rotki/common';
import { useAssets } from '@/modules/assets/use-assets';
import { DialogType } from '@/modules/core/common/dialogs';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useBackendReload } from '@/modules/shell/app/use-backend-reload';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

type ResetType = 'soft' | 'hard';

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
  /** Asks for confirmation, then resets the assets database. */
  showRestoreConfirmation: (type: ResetType) => void;
}

/**
 * Drives the reset-assets-database action: its confirmation, the reset itself, and the reload that
 * has to follow a successful one.
 *
 * @returns whether a reset is running, and the way to start one
 */
export function useRestoreAssetDb(): UseRestoreAssetDbReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { notify } = useNotificationDispatcher();
  const { restoreAssetsDatabase } = useAssets();
  const { reload } = useBackendReload();
  const { show } = useConfirmStore();
  const { useIsActive } = useTaskCenter();

  const loading = useIsActive(ActivityKind.ASSETS, ActivityPart.RESET);

  async function updateComplete(): Promise<void> {
    await reload();
  }

  function showDoneConfirmation(): void {
    show(
      {
        message: t('asset_update.restore.success.description'),
        primaryAction: t('common.actions.ok'),
        singleAction: true,
        title: t('asset_update.restore.success.title'),
        type: DialogType.SUCCESS,
      },
      updateComplete,
    );
  }

  function showDoubleConfirmation(type: ResetType): void {
    show(
      {
        message: t('asset_update.restore.hard_restore_confirmation.message'),
        title: t('asset_update.restore.hard_restore_confirmation.title'),
      },
      async () => restoreAssets(type),
    );
  }

  async function restoreAssets(resetType: ResetType): Promise<void> {
    if (get(loading))
      return;

    const result = await restoreAssetsDatabase(resetType);

    if (result.success) {
      showDoneConfirmation();
      return;
    }

    const { message } = result;
    if (message.includes(UNDELETABLE_ASSETS))
      showDoubleConfirmation(resetType);

    notify({
      display: true,
      message,
      severity: Severity.ERROR,
      title: t('asset_update.restore.title'),
    });
  }

  function showRestoreConfirmation(type: ResetType): void {
    show(
      {
        message: type === 'soft'
          ? t('asset_update.restore.delete_confirmation.soft_reset_message')
          : t('asset_update.restore.delete_confirmation.hard_reset_message'),
        title: t('asset_update.restore.delete_confirmation.title'),
      },
      async () => restoreAssets(type),
    );
  }

  return {
    loading,
    showRestoreConfirmation,
  };
}
