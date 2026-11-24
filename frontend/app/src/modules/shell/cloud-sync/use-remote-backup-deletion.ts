import type { Ref } from 'vue';
import type { RemoteBackup } from '@/modules/session/sync';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { failureCauseOf } from '@/modules/core/api/request-result';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

export const RemoteBackupDeletionPhase = {
  /** Asking the server which backup it stores. */
  LOADING: 'loading',
  /** The server could not say which backup it stores. */
  LOAD_FAILED: 'load_failed',
  /** The server stores no backup, so there is nothing to delete. */
  EMPTY: 'empty',
  /** The backup is shown for the user to review and confirm. */
  REVIEW: 'review',
  DELETING: 'deleting',
  DELETED: 'deleted',
} as const;

export type RemoteBackupDeletionPhase = (typeof RemoteBackupDeletionPhase)[keyof typeof RemoteBackupDeletionPhase];

interface UseRemoteBackupDeletionReturn {
  /** The backup the user reviews, the one a deletion names. A new one asks for a new acknowledgement. */
  backup: Readonly<Ref<RemoteBackup | undefined>>;
  /** Whether the server stored a different backup than the one the user reviewed, so it was shown again. */
  backupChanged: Readonly<Ref<boolean>>;
  /** Why the last load (phase LOAD_FAILED) or deletion (phase REVIEW, backup kept up for another try) failed. */
  failure: Readonly<Ref<unknown>>;
  phase: Readonly<Ref<RemoteBackupDeletionPhase>>;
  /** Asks the server which backup it stores. */
  load: () => Promise<void>;
  /**
   * Deletes the reviewed backup.
   *
   * @param disableSync - turn off this device's automatic backup, so it does not upload one right after
   */
  remove: (disableSync: boolean) => Promise<void>;
}

/**
 * Drives the deletion of the backup stored on the rotki server.
 *
 * @remarks
 * The user reviews the backup before deleting it, and the deletion names that backup's hash, so the
 * server keeps a backup another device uploaded meanwhile. When that happens the new backup is
 * fetched and shown for review. Each opening of the panel takes a new instance, so nothing carries over.
 */
export function useRemoteBackupDeletion(): UseRemoteBackupDeletionReturn {
  const phase = shallowRef<RemoteBackupDeletionPhase>(RemoteBackupDeletionPhase.LOADING);
  const backup = shallowRef<RemoteBackup>();
  const backupChanged = shallowRef<boolean>(false);
  const failure = shallowRef<unknown>();

  const { premiumSync } = storeToRefs(usePremiumStore());
  const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
  const { deleteRemoteBackup, fetchRemoteBackup } = useSyncApi();

  async function load(): Promise<void> {
    set(phase, RemoteBackupDeletionPhase.LOADING);
    set(failure, undefined);
    try {
      const remote = await fetchRemoteBackup();
      set(backup, remote ?? undefined);
      set(phase, remote ? RemoteBackupDeletionPhase.REVIEW : RemoteBackupDeletionPhase.EMPTY);
    }
    catch (error: unknown) {
      set(failure, error);
      set(phase, RemoteBackupDeletionPhase.LOAD_FAILED);
    }
  }

  async function remove(disableSync: boolean): Promise<void> {
    const reviewed = get(backup);
    if (!reviewed || get(phase) !== RemoteBackupDeletionPhase.REVIEW)
      return;

    set(phase, RemoteBackupDeletionPhase.DELETING);
    set(failure, undefined);
    try {
      const { premiumShouldSync } = await deleteRemoteBackup({
        dataHash: reviewed.dataHash,
        disableSync,
      });
      set(premiumSync, premiumShouldSync);
      set(lastDataUpload, 0);
      set(backup, undefined);
      set(phase, RemoteBackupDeletionPhase.DELETED);
    }
    catch (error: unknown) {
      if (failureCauseOf(error) === FailureCause.CONFLICT) {
        set(backupChanged, true);
        await load();
      }
      else {
        set(failure, error);
        set(phase, RemoteBackupDeletionPhase.REVIEW);
      }
    }
  }

  return {
    backup: readonly(backup),
    backupChanged: readonly(backupChanged),
    failure: readonly(failure),
    load,
    phase: readonly(phase),
    remove,
  };
}
