import { useLocalStorage } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { err, none, ok, type OptionType as Option, type ResultType as Result, some } from 'plainfp';
import { isErr } from 'plainfp/result';
import { ApplyUpdateKind } from '@/modules/assets/types';
import { useAssets } from '@/modules/assets/use-assets';
import { AUTO_APPLY_ASSET_UPDATES_KEY, SKIPPED_ASSET_VERSION_KEY } from '@/modules/shell/app/asset-update-keys';
import { BackendRestartStatus, useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useAssetUpdateThrottle } from './use-asset-update-throttle';
import {
  type ApplyOutcome,
  type Resolution,
  type UnlockError,
  UnlockErrorKind,
  type UpdateChanges,
  UpdateOutcomeKind,
} from './use-unlock-flow';

export interface AssetUpdateSteps {
  autoApplyUpdates: () => boolean;
  checkUpdate: () => Promise<Result<Option<UpdateChanges>, UnlockError>>;
  applyUpdate: (upToVersion: number, resolution?: Resolution) => Promise<Result<ApplyOutcome, UnlockError>>;
  requestRestart: () => Promise<Result<void, UnlockError>>;
  waitReady: () => Promise<Result<void, UnlockError>>;
}

/**
 * The asset-update + backend-restart steps of the unlock flow. Self-contained so
 * the rest of the flow (authenticate/connect/unlock/loadSession) stays focused on
 * the session.
 */
export function useAssetUpdateSteps(): AssetUpdateSteps {
  const { applyUpdates, checkForUpdate } = useAssets();
  const { restartBackend } = useBackendManagement();
  const updateThrottle = useAssetUpdateThrottle();
  const skipped = useLocalStorage<number>(SKIPPED_ASSET_VERSION_KEY, 0);
  const autoApply = useLocalStorage<boolean>(AUTO_APPLY_ASSET_UPDATES_KEY, false);

  return {
    applyUpdate: async (upToVersion, resolution): Promise<Result<ApplyOutcome, UnlockError>> => {
      const outcome = await applyUpdates({ resolution, version: upToVersion });
      if (isErr(outcome))
        return err({ kind: UnlockErrorKind.updateFailed, message: outcome.error.message });
      const result = outcome.value;
      if (result.kind === ApplyUpdateKind.CONFLICTS)
        return ok({ conflicts: result.conflicts, kind: UpdateOutcomeKind.conflicts });
      return ok({ kind: UpdateOutcomeKind.done });
    },
    autoApplyUpdates: (): boolean => get(autoApply) === true,
    checkUpdate: async (): Promise<Result<Option<UpdateChanges>, UnlockError>> => {
      if (sessionStorage.getItem('skip_update'))
        return ok(none);
      if (!updateThrottle.shouldCheck())
        return ok(none);
      const outcome = await checkForUpdate();
      if (isErr(outcome))
        return ok(none);
      updateThrottle.recordCheck();
      const { updateAvailable, versions } = outcome.value;
      // A skipped version stays skipped only while updates ask first; applying them automatically supersedes it.
      if (!updateAvailable || !versions || (!get(autoApply) && get(skipped) === versions.remote))
        return ok(none);
      return ok(some({
        changes: versions.newChanges,
        local: versions.local,
        remote: versions.remote,
        upToVersion: versions.remote,
      }));
    },
    requestRestart: async (): Promise<Result<void, UnlockError>> => {
      const result = await restartBackend();
      if (result.status === BackendRestartStatus.failed)
        return err({ kind: UnlockErrorKind.restartFailed });

      return ok(undefined);
    },
    waitReady: async (): Promise<Result<void, UnlockError>> => ok(undefined),
  };
}
