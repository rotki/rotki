import { err, none, ok, type OptionType as Option, type ResultType as Result, some } from 'plainfp';
import { useAssets } from '@/modules/assets/use-assets';
import { SKIPPED_ASSET_VERSION_KEY } from '@/modules/shell/app/asset-update-keys';
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

  return {
    applyUpdate: async (upToVersion, resolution): Promise<Result<ApplyOutcome, UnlockError>> => {
      const result = await applyUpdates({ resolution, version: upToVersion });
      if (result.done)
        return ok({ kind: UpdateOutcomeKind.done });
      if (result.conflicts)
        return ok({ conflicts: result.conflicts, kind: UpdateOutcomeKind.conflicts });
      return err({ kind: UnlockErrorKind.updateFailed, message: 'the asset update did not complete' });
    },
    checkUpdate: async (): Promise<Result<Option<UpdateChanges>, UnlockError>> => {
      if (sessionStorage.getItem('skip_update'))
        return ok(none);
      if (!updateThrottle.shouldCheck())
        return ok(none);
      const { updateAvailable, versions } = await checkForUpdate();
      updateThrottle.recordCheck();
      if (!updateAvailable || !versions || get(skipped) === versions.remote)
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
