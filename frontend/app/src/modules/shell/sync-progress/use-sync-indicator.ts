import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { useLogout } from '@/modules/auth/use-logout';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How often the cloud icon alternates while a sync is in flight, in milliseconds. */
const ICON_TICK = 600;

/** The upload phases worth animating; encrypting is too brief to be worth a moving icon. */
const ANIMATED_PHASES = ['compressing', 'uploading'];

interface UseSyncIndicatorReturn {
  /** Cancels a running force sync and clears whatever status it left behind. */
  cancelForceSync: () => Promise<void>;
  /** Abandons the pending confirmation without syncing. */
  cancelSync: () => void;
  /** Forgets the outcome of the last upload, and any progress it left behind. */
  clearUploadStatus: () => void;
  /** Whether the user's plan includes cloud backup. */
  cloudBackupAllowed: Ref<boolean>;
  /** Two-way binding for the confirmation's acknowledgement checkbox. */
  confirmChecked: Ref<boolean>;
  /** What the upload is currently doing, as a sentence. */
  currentProgressText: ComputedRef<string>;
  /** Whether the confirmation dialog is showing. */
  displaySyncConfirmation: Ref<boolean>;
  /** The animated cloud icon for the direction being synced. */
  icon: ComputedRef<RuiIcons>;
  /** Whether the pending sync pulls the remote database down over the local one. */
  isDownload: ComputedRef<boolean>;
  /** Whether a sync is running. */
  isSyncing: ComputedRef<boolean>;
  /** The confirmation's body text, which differs by direction. */
  message: ComputedRef<string>;
  /** Whether the menu is open. */
  modelVisible: Ref<boolean>;
  /** Whether the sync settings submenu is open, which pins the menu open. */
  modelSyncSettingMenuOpen: Ref<boolean>;
  /** Whether a force sync is in flight from this menu. */
  pending: Readonly<Ref<boolean>>;
  /** Runs the confirmed sync, logging out afterwards when it replaced the local database. */
  performSync: () => Promise<void>;
  /**
   * Opens the confirmation for a direction.
   *
   * @remarks
   * A sync overwrites one side wholesale, so nothing runs until {@link UseSyncIndicatorReturn.performSync}
   * is called from the confirmed dialog.
   */
  showConfirmation: (action: SyncAction) => void;
  /** Pluralisation choice for the confirmation's title and action, by direction. */
  textChoice: ComputedRef<number>;
  /** The activator's tooltip, which reports a failed upload ahead of anything else. */
  tooltip: ComputedRef<string>;
  /** How far the running upload has got, or undefined when none is running. */
  uploadProgress: Ref<DatabaseUploadProgress | undefined>;
  /** The icon for the current upload phase. */
  uploadProgressIcon: ComputedRef<RuiIcons>;
  /** The outcome of the last upload, or null when it succeeded or none has run. */
  uploadStatus: Ref<DbUploadResult | null>;
}

/**
 * Drives the cloud sync menu: its icons and tooltip, the confirmation before a sync, and cancelling
 * one that is running.
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
  const { cancelActivity } = useNativeTask();
  const { useIsActive } = useTaskCenter();
  const { logout } = useLogout();

  const isSyncing = useIsActive(ActivityKind.SYNC);

  const isDownload = computed<boolean>(() => get(syncAction) === SYNC_DOWNLOAD);

  const textChoice = computed<number>(() => (get(syncAction) === SYNC_UPLOAD ? 1 : 2));

  const message = computed<string>(() =>
    get(syncAction) === SYNC_UPLOAD
      ? t('sync_indicator.upload_confirmation.message_upload')
      : t('sync_indicator.upload_confirmation.message_download'),
  );

  const { counter, pause, resume } = useInterval(ICON_TICK, {
    controls: true,
    immediate: false,
  });

  const icon = computed<RuiIcons>(() => {
    const tick = get(counter) % 2 === 0;
    if (get(isDownload))
      return tick ? 'lu-cloud-download-2-fill' : 'lu-cloud-download-fill';

    return tick ? 'lu-cloud-upload-2-fill' : 'lu-cloud-upload-fill';
  });

  const uploadProgressIcon = computed<RuiIcons>(() => {
    const progress = get(uploadProgress);
    if (!progress)
      return 'lu-cloud-fill';

    const tick = get(counter) % 2 === 0;

    switch (progress.type) {
      case 'compressing':
        return tick ? 'lu-folder-shrink-1' : 'lu-folder-shrink-2';
      case 'encrypting':
        return 'lu-shield';
      case 'uploading':
        return tick ? 'lu-cloud-upload-2-fill' : 'lu-cloud-upload-fill';
      default:
        return 'lu-cloud-fill';
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

  const currentProgressText = computed<string>(() => {
    if (!isDefined(uploadProgress))
      return '';

    switch (get(uploadProgress).type) {
      case 'compressing':
        return t('sync_indicator.upload_progress.compressing');
      case 'encrypting':
        return t('sync_indicator.upload_progress.encrypting');
      case 'uploading':
        return t('sync_indicator.upload_progress.uploading');
      default:
        return '';
    }
  });

  function showConfirmation(action: SyncAction): void {
    set(modelVisible, false);
    showSyncConfirmation(action);
  }

  async function performSync(): Promise<void> {
    if (get(syncAction) === SYNC_UPLOAD)
      clearUploadStatus();

    set(pending, true);
    await forceSync(logout);
    set(pending, false);
  }

  async function cancelForceSync(): Promise<void> {
    cancelActivity(ActivityKind.SYNC);
    await nextTick(() => clearUploadStatus());
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

  watch(isSyncing, stopSyncWhenItFinishes);
  watchImmediate(runCounter, animateWhileWorking);

  return {
    cancelForceSync,
    cancelSync,
    clearUploadStatus,
    cloudBackupAllowed,
    confirmChecked,
    currentProgressText,
    displaySyncConfirmation,
    icon,
    isDownload,
    isSyncing,
    message,
    modelSyncSettingMenuOpen,
    modelVisible,
    pending: readonly(pending),
    performSync,
    showConfirmation,
    textChoice,
    tooltip,
    uploadProgress,
    uploadProgressIcon,
    uploadStatus,
  };
}
