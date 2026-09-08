import type { DatabaseUploadProgress, DbUploadResult } from '../types/shared-types';
import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useSync } from '@/modules/session/use-session-sync';

export function createDbUploadResultHandler(): StateHandler<DbUploadResult> {
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
  const { uploadProgress } = useSync();

  return createStateHandler<DatabaseUploadProgress>((data) => {
    set(uploadProgress, data);
  });
}
