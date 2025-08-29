import type { DatabaseUploadProgress, DbUploadResult } from '../types/shared-types';
import type { StateHandler } from '@/modules/messaging/interfaces';
import { useSync } from '@/composables/session/sync';
import { createStateHandler } from '@/modules/messaging/utils';

export function createDbUploadResultHandler(): StateHandler<DbUploadResult> {
  // Capture refs at handler creation time (in setup context)
  const { uploadProgress, uploadStatus, uploadStatusAlreadyHandled } = useSync();

  return createStateHandler<DbUploadResult>((data) => {
    set(uploadProgress, undefined);

    if (data.uploaded) {
      set(uploadStatus, undefined);
      set(uploadStatusAlreadyHandled, false);
    }
    else {
      if (get(uploadStatusAlreadyHandled))
        return;

      set(uploadStatus, data);
      set(uploadStatusAlreadyHandled, true);
    }
  });
}

export function createDbUploadProgressHandler(): StateHandler<DatabaseUploadProgress> {
  // Capture ref at handler creation time (in setup context)
  const { uploadProgress } = useSync();

  return createStateHandler<DatabaseUploadProgress>((data) => {
    set(uploadProgress, data);
  });
}
