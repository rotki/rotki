import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { useLogout } from '@/modules/auth/use-logout';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How often the cloud icon alternates while a sync is in flight, in milliseconds. */
const ICON_TICK = 600;

/** The upload phases worth animating; encrypting is too brief to be worth a moving icon. */
const ANIMATED_PHASES = ['compressing', 'uploading'];

interface UseSyncIndicatorReturn {
  /** Abandons the pending confirmation without syncing. */
  cancelSync: () => void;
  /** Whether the user's plan includes cloud backup. */
  cloudBackupAllowed: Ref<boolean>;
  /** Two-way binding for the confirmation's acknowledgement checkbox. */
  confirmChecked: Ref<boolean>;
  /** Whether the menu shows the confirmation in place of the sync buttons. */
  displaySyncConfirmation: Ref<boolean>;
  /** The animated cloud icon for the direction being synced. */
  icon: ComputedRef<RuiIcons>;
  /** Whether the pending sync pulls the remote database down over the local one. */
  isDownload: ComputedRef<boolean>;
  /** Whether a sync is running. */
  isSyncing: ComputedRef<boolean>;
  /** Whether the menu is open. */
  modelVisible: Ref<boolean>;
  /** Whether the sync settings submenu is open, which pins the menu open. */
  modelSyncSettingMenuOpen: Ref<boolean>;
  /** Whether a force sync is in flight from this menu. */
  pending: Readonly<Ref<boolean>>;
  /** Runs the confirmed sync, logging out afterwards when it replaced the local database. */
  performSync: () => Promise<void>;
  /**
   * Opens the confirmation for a direction, in place inside the open menu.
   *
   * @remarks
   * A sync overwrites one side wholesale, so nothing runs until {@link UseSyncIndicatorReturn.performSync}
   * is called from the confirmation. Closing the menu abandons it.
   */
  showConfirmation: (action: SyncAction) => void;
  /** The activator's tooltip, which reports a failed upload ahead of anything else. */
  tooltip: ComputedRef<string>;
  /** How far the running upload has got, or undefined when none is running. */
  uploadProgress: Ref<DatabaseUploadProgress | undefined>;
  /** The icon for the current upload phase. */
  uploadProgressIcon: ComputedRef<RuiIcons>;
  /** The outcome of the last upload, or null when it succeeded or none has run. */
  uploadStatus: Ref<DbUploadResult | null>;
  /** Whether balances or token detection are loading, which holds back a sync. */
  waitingForBalances: Readonly<Ref<boolean>>;
}

/**
 * Drives the cloud sync menu: its icons and tooltip and the confirmation before a sync. A running
 * sync reports, and is cancelled, from its row in the dock.
 *
 * @returns the menu state and the actions its controls call
 */
export function useSyncIndicator(): UseSyncIndicatorReturn {
  const modelSyncSettingMenuOpen = shallowRef<boolean>(false);
  const modelVisible = shallowRef<boolean>(false);
  const pending = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const { allowed: cloudBackupAllowed } = useFeatureAccess(PremiumFeature.CLOUD_BACKUP);
  const {
    cancelSync,
    clearUploadStatus,
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
  } = useSync();
  const { useIsActive } = useTaskCenter();
  const { logout } = useLogout();
  const { loadingBalancesAndDetection: waitingForBalances } = useBalancesLoading();

  const isSyncing = useIsActive(ActivityKind.SYNC);

  const isDownload = computed<boolean>(() => get(syncAction) === SYNC_DOWNLOAD);

  const { counter, pause, resume } = useInterval(ICON_TICK, {
    controls: true,
    immediate: false,
  });

  const icon = computed<RuiIcons>(() => {
    const tick = get(counter) % 2 === 0;
    if (get(isDownload))
      return tick ? 'lu-cloud-download-2' : 'lu-cloud-download';

    return tick ? 'lu-cloud-upload-2' : 'lu-cloud-upload';
  });

  const uploadProgressIcon = computed<RuiIcons>(() => {
    const progress = get(uploadProgress);
    if (!progress)
      return 'lu-cloud';

    const tick = get(counter) % 2 === 0;

    switch (progress.type) {
      case 'compressing':
        return tick ? 'lu-folder-shrink-1' : 'lu-folder-shrink-2';
      case 'encrypting':
        return 'lu-shield';
      case 'uploading':
        return tick ? 'lu-cloud-upload-2' : 'lu-cloud-upload';
      default:
        return 'lu-cloud';
    }
  });

  const tooltip = computed<string>(() => {
    if (!get(cloudBackupAllowed))
      return t('sync_indicator.cloud_backup_unavailable');

    if (get(uploadStatus)) {
      const title = t('sync_indicator.db_upload_result.title');
      const message = t('sync_indicator.db_upload_result.message', {
        reason: get(uploadStatus)?.message,
      });
      return `${title}: ${message}`;
    }
    return t('sync_indicator.menu_tooltip');
  });

  function showConfirmation(action: SyncAction): void {
    showSyncConfirmation(action);
  }

  async function performSync(): Promise<void> {
    if (get(syncAction) === SYNC_UPLOAD)
      clearUploadStatus();

    set(pending, true);
    await forceSync(logout);
    set(pending, false);
  }

  const runCounter = computed<boolean>(() => {
    if (get(pending))
      return true;

    const type = get(uploadProgress)?.type;
    return !!type && ANIMATED_PHASES.includes(type);
  });

  function stopSyncWhenItFinishes(current: boolean, previous: boolean): void {
    if (current !== previous && !current)
      cancelSync();
  }

  function animateWhileWorking(running: boolean): void {
    if (running)
      resume();
    else
      pause();
  }

  /** The confirmation lives in the menu, so closing the menu before confirming abandons it. */
  function abandonConfirmationOnClose(visible: boolean): void {
    if (!visible && !get(pending))
      cancelSync();
  }

  watch(isSyncing, stopSyncWhenItFinishes);
  watch(modelVisible, abandonConfirmationOnClose);
  watchImmediate(runCounter, animateWhileWorking);

  return {
    cancelSync,
    cloudBackupAllowed,
    confirmChecked,
    displaySyncConfirmation,
    icon,
    isDownload,
    isSyncing,
    modelSyncSettingMenuOpen,
    modelVisible,
    pending: readonly(pending),
    performSync,
    showConfirmation,
    tooltip,
    uploadProgress,
    uploadProgressIcon,
    uploadStatus,
    waitingForBalances,
  };
}
