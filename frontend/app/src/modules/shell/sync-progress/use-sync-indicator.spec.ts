import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { createMock } from '@test/utils/create-mock';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useSyncIndicator } from './use-sync-indicator';

let cloudBackupAllowed: Ref<boolean>;
let syncAction: Ref<SyncAction | undefined>;
let uploadProgress: Ref<DatabaseUploadProgress | undefined>;
let uploadStatus: Ref<DbUploadResult | null>;
let displaySyncConfirmation: Ref<boolean>;
let confirmChecked: Ref<boolean>;
let isSyncing: Ref<boolean>;
let scope: ReturnType<typeof effectScope>;

const {
  cancelActivity,
  cancelSync,
  clearUploadStatus,
  forceSync,
  logout,
  showSyncConfirmation,
} = vi.hoisted(() => ({
  cancelActivity: vi.fn(),
  cancelSync: vi.fn(),
  clearUploadStatus: vi.fn(),
  forceSync: vi.fn(async () => Promise.resolve()),
  logout: vi.fn(),
  showSyncConfirmation: vi.fn(),
}));

vi.mock('@/modules/session/use-session-sync', () => ({
  useSync: (): Record<string, unknown> => ({
    cancelSync,
    clearUploadStatus,
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
  }),
}));

vi.mock('@/modules/premium/use-feature-access', async () => {
  const actual = await vi.importActual<typeof import('@/modules/premium/use-feature-access')>(
    '@/modules/premium/use-feature-access',
  );
  return {
    ...actual,
    useFeatureAccess: (): Record<string, unknown> => ({ allowed: cloudBackupAllowed }),
  };
});

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): Record<string, unknown> => ({ cancelActivity }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): Ref<boolean> => isSyncing }),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): Record<string, unknown> => ({ logout }),
}));

function progressOf(type: DatabaseUploadProgress['type']): DatabaseUploadProgress {
  return type === 'uploading' ? { currentChunk: 1, totalChunks: 4, type } : { type };
}

function uploadFailure(message: string): DbUploadResult {
  return { actionable: true, message, uploaded: false };
}

function indicator(): ReturnType<typeof useSyncIndicator> {
  scope = effectScope();
  return scope.run(() => useSyncIndicator())!;
}

describe('modules/shell/sync-progress/useSyncIndicator', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers();
    cloudBackupAllowed = ref<boolean>(true);
    syncAction = shallowRef<SyncAction>();
    uploadProgress = ref<DatabaseUploadProgress>();
    uploadStatus = ref<DbUploadResult | null>(null);
    displaySyncConfirmation = ref<boolean>(false);
    confirmChecked = ref<boolean>(false);
    isSyncing = ref<boolean>(false);
  });

  afterEach(() => {
    scope?.stop();
    vi.useRealTimers();
  });

  describe('the confirmation before a sync', () => {
    it('should sync nothing when the confirmation is only opened', () => {
      const { showConfirmation } = indicator();
      showConfirmation(SYNC_DOWNLOAD);

      expect(showSyncConfirmation).toHaveBeenCalledWith(SYNC_DOWNLOAD);
      expect(forceSync).not.toHaveBeenCalled();
    });

    it('should close the menu when it opens the confirmation', () => {
      const { modelVisible, showConfirmation } = indicator();
      set(modelVisible, true);
      showConfirmation(SYNC_UPLOAD);

      expect(get(modelVisible)).toBe(false);
    });

    it('should sync nothing when the confirmation is cancelled', () => {
      const { cancelSync: cancel, showConfirmation } = indicator();
      showConfirmation(SYNC_DOWNLOAD);
      cancel();

      expect(cancelSync).toHaveBeenCalledOnce();
      expect(forceSync).not.toHaveBeenCalled();
    });

    it('should run the sync only once confirmed, and hand it the logout', async () => {
      const { performSync, showConfirmation } = indicator();
      showConfirmation(SYNC_DOWNLOAD);
      expect(forceSync).not.toHaveBeenCalled();

      await performSync();

      expect(forceSync).toHaveBeenCalledWith(logout);
    });

    it('should mark the sync pending only while it runs', async () => {
      const { pending, performSync } = indicator();

      const running = performSync();
      expect(get(pending)).toBe(true);

      await running;
      expect(get(pending)).toBe(false);
    });

    it('should forget a previous upload failure before uploading again', async () => {
      set(syncAction, SYNC_UPLOAD);

      const { performSync } = indicator();
      await performSync();

      expect(clearUploadStatus).toHaveBeenCalledOnce();
    });

    it('should keep the upload failure showing when the sync is a download', async () => {
      set(syncAction, SYNC_DOWNLOAD);

      const { performSync } = indicator();
      await performSync();

      expect(clearUploadStatus).not.toHaveBeenCalled();
    });
  });

  describe('the confirmation wording', () => {
    it.each([
      [SYNC_UPLOAD, 1, 'sync_indicator.upload_confirmation.message_upload', false],
      [SYNC_DOWNLOAD, 2, 'sync_indicator.upload_confirmation.message_download', true],
    ])('should describe a %s', (action, choice, expectedMessage, download) => {
      set(syncAction, action);

      const { isDownload, message, textChoice } = indicator();

      expect(get(textChoice)).toBe(choice);
      expect(get(message)).toBe(expectedMessage);
      expect(get(isDownload)).toBe(download);
    });
  });

  describe('cancelling a running sync', () => {
    it('should cancel the sync activity and clear what it left behind', async () => {
      const { cancelForceSync } = indicator();
      await cancelForceSync();
      await flushPromises();

      expect(cancelActivity).toHaveBeenCalledWith(ActivityKind.SYNC);
      expect(clearUploadStatus).toHaveBeenCalledOnce();
    });

    it('should abandon the pending sync when a running one finishes', async () => {
      set(isSyncing, true);
      indicator();

      set(isSyncing, false);
      await flushPromises();

      expect(cancelSync).toHaveBeenCalledOnce();
    });

    it('should not abandon anything when a sync starts', async () => {
      indicator();

      set(isSyncing, true);
      await flushPromises();

      expect(cancelSync).not.toHaveBeenCalled();
    });
  });

  describe('the tooltip', () => {
    it('should say cloud backup is unavailable before anything else', () => {
      set(cloudBackupAllowed, false);
      set(uploadStatus, uploadFailure('too big'));

      const { tooltip } = indicator();

      expect(get(tooltip)).toBe('sync_indicator.cloud_backup_unavailable');
    });

    it('should report the reason the last upload failed', () => {
      set(uploadStatus, uploadFailure('too big'));

      const { tooltip } = indicator();

      expect(get(tooltip)).toContain('too big');
    });

    it('should otherwise name the menu', () => {
      const { tooltip } = indicator();

      expect(get(tooltip)).toBe('sync_indicator.menu_tooltip');
    });
  });

  describe('the progress text', () => {
    it('should be empty while nothing is uploading', () => {
      const { currentProgressText } = indicator();

      expect(get(currentProgressText)).toBe('');
    });

    it.each([
      ['compressing', 'sync_indicator.upload_progress.compressing'],
      ['encrypting', 'sync_indicator.upload_progress.encrypting'],
      ['uploading', 'sync_indicator.upload_progress.uploading'],
    ] as const)('should name the %s phase', (type, expected) => {
      set(uploadProgress, progressOf(type));

      const { currentProgressText } = indicator();

      expect(get(currentProgressText)).toBe(expected);
    });
  });

  describe('the animated icons', () => {
    it('should point the arrow down for a download and up for an upload', () => {
      set(syncAction, SYNC_DOWNLOAD);
      const download = indicator();
      expect(get(download.icon)).toContain('cloud-download');

      scope.stop();
      set(syncAction, SYNC_UPLOAD);
      const upload = indicator();
      expect(get(upload.icon)).toContain('cloud-upload');
    });

    it('should show a still cloud while nothing is uploading', () => {
      const { uploadProgressIcon } = indicator();

      expect(get(uploadProgressIcon)).toBe('lu-cloud-fill');
    });

    it('should not animate the encrypting phase', () => {
      set(uploadProgress, progressOf('encrypting'));

      const { uploadProgressIcon } = indicator();

      expect(get(uploadProgressIcon)).toBe('lu-shield');
      vi.advanceTimersByTime(1200);
      expect(get(uploadProgressIcon)).toBe('lu-shield');
    });

    it.each(['compressing', 'uploading'] as const)('should alternate the icon while %s', async (type) => {
      set(uploadProgress, progressOf(type));

      const { uploadProgressIcon } = indicator();
      const first = get(uploadProgressIcon);
      await vi.advanceTimersByTimeAsync(600);

      expect(get(uploadProgressIcon)).not.toBe(first);
    });

    it('should fall back to a still cloud for a phase it does not know', () => {
      set(uploadProgress, createMock<DatabaseUploadProgress>());

      const { currentProgressText, uploadProgressIcon } = indicator();

      expect(get(uploadProgressIcon)).toBe('lu-cloud-fill');
      expect(get(currentProgressText)).toBe('');
    });

    it('should hold the icon still once the upload finishes', async () => {
      set(uploadProgress, progressOf('compressing'));

      const { uploadProgressIcon } = indicator();
      set(uploadProgress, undefined);
      await flushPromises();

      const still = get(uploadProgressIcon);
      await vi.advanceTimersByTimeAsync(1200);

      expect(get(uploadProgressIcon)).toBe(still);
    });
  });
});
