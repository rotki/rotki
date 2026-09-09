import type { ActionStatus } from '@/modules/core/common/action';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { assert } from '@rotki/common';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

export interface UseFrontendSettingsWriterReturn {
  updateFrontendSetting: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;
}

/**
 * Serialises every frontend-settings write, app-wide.
 *
 * The repo is only updated once a request resolves, so two writes to the same key resolving out of
 * order would leave it holding the value the backend did not keep.
 *
 * Module scope on purpose - the callers are separate composable instances and the queue has to be
 * shared by all of them.
 */
let pendingWrite: Promise<unknown> = Promise.resolve();

/**
 * Persists a patch of frontend settings.
 *
 * Split out of `useSettingsOperations` because that composable resolves the notification surface,
 * and so may only be called from a component `setup`. Callers that write settings from outside a
 * component - the notification cooldown records a display from the notification store itself -
 * would otherwise pull `useI18n` into a context that has no current instance, and close a cycle
 * back onto notifications. This holds nothing but the repo and the API.
 */
export function useFrontendSettingsWriter(): UseFrontendSettingsWriterReturn {
  const repo = useSettingsRepo();
  const api = useSettingsApi();

  /**
   * Persists a patch over the frontend settings blob.
   *
   * @remarks
   * Sends only the changed keys, so keys a newer rotki wrote survive. The repo is merged from the
   * payload rather than re-read, so post-persist effects run only for the changed keys.
   *
   * @param payload - the keys to change
   * @returns whether the write reached the backend, carrying its message when it did not
   */
  async function write(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    try {
      await api.patchFrontendSettings(payload);
      repo.updateFrontend(payload);

      return {
        success: true,
      };
    }
    catch (error: unknown) {
      logger.error(error);
      return {
        message: getErrorMessage(error),
        success: false,
      };
    }
  }

  async function updateFrontendSetting(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    const props = Object.keys(payload);
    // Rejects before queueing, so a caller's bug cannot stall every later write.
    assert(props.length > 0, 'Payload must be not-empty');

    const queued = pendingWrite.then(async () => write(payload));
    // `write` never rejects, but keep the chain alive regardless: one failure must not block the app.
    pendingWrite = queued.catch(() => undefined);
    return queued;
  }

  return { updateFrontendSetting };
}
