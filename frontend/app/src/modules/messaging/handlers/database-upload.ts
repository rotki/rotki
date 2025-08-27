import type { DatabaseUploadProgress, DbUploadResult } from '../types/shared-types';
import type { StateHandler } from '@/modules/messaging/interfaces';
import { useSync } from '@/composables/session/sync';
import { createStateHandler } from '@/modules/messaging/utils';

export function createDbUploadResultHandler(): StateHandler<DbUploadResult> {
  return createStateHandler<DbUploadResult>((data) => {
    const { uploadProgress, uploadStatus, uploadStatusAlreadyHandled } = useSync();

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
  return createStateHandler<DatabaseUploadProgress>((data) => {
    const { uploadProgress } = useSync();
    set(uploadProgress, data);
  });
}
