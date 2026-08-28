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
 * The wire format is a patch merged by the backend, so two writes to *different* keys no longer
 * clobber each other the way rebuilding the whole blob from the repo did. What the queue still
 * buys is ordering: the repo is only updated once a request resolves, so two writes to the *same*
 * key that resolve out of order would leave the local repo holding the value the backend did not
 * keep. Serialising makes the local and the persisted order the same one.
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
   * Only the changed keys go over the wire, and the backend merges them into the stored blob, so a
   * key this version's schema does not declare - one a newer rotki wrote - is left alone instead of
   * being deleted by a write rebuilt from the repo's already-parsed view.
   *
   * The repo is then merged from that same payload rather than re-read from the backend. An unknown
   * key cannot live in a parsed FrontendSettings either way, so re-reading would buy nothing, and it
   * would run the registry's post-persist effects (BigNumber format, mirror syncs) over every key
   * instead of over the ones that actually changed.
   *
   * @param payload - the keys to change, which the backend merges into the stored blob
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
