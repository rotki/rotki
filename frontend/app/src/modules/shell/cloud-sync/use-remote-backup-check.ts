import type { Ref } from 'vue';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

/** How long a "no backup" answer is trusted before the menu asks the server again. */
const CHECK_INTERVAL_MS = 3_600_000;

interface UseRemoteBackupCheckReturn {
  /** Whether the server is being asked for its backup. */
  checking: Readonly<Ref<boolean>>;
  /** Asks the server for its backup when none is known and the last check is over an hour old. */
  checkIfUnknown: () => Promise<void>;
}

/**
 * Keeps the sync menu's last upload time honest when it reads never.
 *
 * @remarks
 * That time is only read at login and on uploads, so a backup made since by another device stays
 * unknown here. Asking the server whenever the menu opens would query it on every glance, so it is
 * asked only while no backup is known, at most once an hour. The backend keeps the answer, so the
 * periodic refresh reports it from then on.
 */
export function useRemoteBackupCheck(): UseRemoteBackupCheckReturn {
  const checking = shallowRef<boolean>(false);

  const { lastDataUpload, lastRemoteBackupCheck } = storeToRefs(useSessionMetadataStore());
  const { fetchRemoteBackup } = useSyncApi();

  async function checkIfUnknown(): Promise<void> {
    if (get(lastDataUpload) || get(checking) || Date.now() - get(lastRemoteBackupCheck) < CHECK_INTERVAL_MS)
      return;

    set(lastRemoteBackupCheck, Date.now());
    set(checking, true);
    try {
      const backup = await fetchRemoteBackup();
      set(lastDataUpload, backup?.uploadTs ?? 0);
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error))
        logger.warn('Could not check the server for a backup', error);
    }
    finally {
      set(checking, false);
    }
  }

  return {
    checking: readonly(checking),
    checkIfUnknown,
  };
}
