import type { ActionStatus } from '@/modules/core/common/action';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { assert } from '@rotki/common';
import { snakeCaseTransformer } from '@/modules/core/api/transformers';
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
 * The wire format is the whole settings blob, rebuilt from the repo, and the repo is only updated
 * once the request resolves. Two writes in flight at the same time would therefore both build the
 * blob from the pre-update repo, each carrying the other's stale value, and the later response
 * would win. That needs no unusual timing: any two settings changed within one round trip hit it,
 * including from different components, and it leaves the merged local repo looking correct while
 * the backend holds the loser.
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
   * The repo is read inside the queued turn, so a write builds on whatever the previous one
   * persisted rather than on a snapshot taken before it ran. Only the patch goes back to the repo:
   * it runs the registry's post-persist effects and mirror syncs for the keys that actually changed.
   *
   * @param payload - the keys to change, which are merged over the whole stored blob
   * @returns whether the write reached the backend, carrying its message when it did not
   */
  async function write(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    try {
      const updatedSettings = { ...repo.frontend, ...payload };
      await api.setSettings({
        frontendSettings: JSON.stringify(snakeCaseTransformer(updatedSettings)),
      });

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
