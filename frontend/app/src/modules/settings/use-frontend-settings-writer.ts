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

  async function updateFrontendSetting(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const updatedSettings = { ...repo.frontend, ...payload };
      await api.setSettings({
        frontendSettings: JSON.stringify(snakeCaseTransformer(updatedSettings)),
      });

      // Merge only the patch: the repo runs the registry's post-persist effects (BigNumber format)
      // and mirror syncs for the keys that actually changed.
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

  return { updateFrontendSetting };
}
