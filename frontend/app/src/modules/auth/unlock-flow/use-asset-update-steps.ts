import { err, none, ok, type OptionType as Option, type ResultType as Result, some } from 'plainfp';
import { useAssets } from '@/modules/assets/use-assets';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
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
  const { isPackaged } = useInterop();
  const updateThrottle = useAssetUpdateThrottle();
  // A specific remote version the user permanently skipped (shared with AssetUpdateMessage).
  const skipped = useLocalStorage<number>('rotki_skip_asset_db_version', 0);

  return {
    applyUpdate: async (upToVersion, resolution): Promise<Result<ApplyOutcome, UnlockError>> => {
      const result = await applyUpdates({ resolution, version: upToVersion });
      if (result.done)
        return ok({ kind: UpdateOutcomeKind.done });
      if (result.conflicts)
        return ok({ conflicts: result.conflicts, kind: UpdateOutcomeKind.conflicts });
      return err({ kind: UnlockErrorKind.updateFailed, message: 'the asset update did not complete' });
    },
    // Throttled to the first login per calendar day (or after a rotki app-version change):
    // asset updates ship on a days-to-weeks cadence, so checking on every login is wasteful.
    // Honours both skip mechanisms — the per-run `skip_update` flag (set from the URL in
    // main.ts, used by e2e) and the per-version `rotki_skip_asset_db_version`. Only
    // `loginSteps` reaches this — create/resume override `checkUpdate` to always `none`.
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
      // Electron restarts its managed process; on web the restart is a no-op until
      // the orchestrator's HTTP control endpoint lands. `restarting` is a flow phase
      // either way — it never tears the app down to the global "connecting" state.
      if (isPackaged)
        await restartBackend();
      return ok(undefined);
    },
    // No real wait needed yet: web restart is a no-op and Electron's restartBackend
    // already reconnects before it resolves.
    waitReady: async (): Promise<Result<void, UnlockError>> => ok(undefined),
  };
}
