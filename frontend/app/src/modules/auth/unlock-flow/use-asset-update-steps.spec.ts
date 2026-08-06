import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendRestartStatus } from '@/modules/shell/app/use-backend-management';
import { useAssetUpdateSteps } from './use-asset-update-steps';
import { UnlockErrorKind } from './use-unlock-flow';

const { applyUpdates, checkForUpdate, interopState, restartBackend } = vi.hoisted(() => ({
  applyUpdates: vi.fn(),
  checkForUpdate: vi.fn(),
  interopState: { isPackaged: false },
  restartBackend: vi.fn(),
}));

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: vi.fn(() => ({ applyUpdates, checkForUpdate })),
}));

vi.mock('@/modules/shell/app/use-backend-management', async importOriginal => ({
  // The status constants are values the code under test compares against, so the real
  // ones have to come through; only the composable is replaced.
  ...(await importOriginal<typeof import('@/modules/shell/app/use-backend-management')>()),
  useBackendManagement: vi.fn(() => ({ restartBackend })),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({ isPackaged: interopState.isPackaged })),
}));

describe('useAssetUpdateSteps', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    interopState.isPackaged = false;
  });

  describe('checkUpdate (throttled)', () => {
    it('should hit the network on the first login of the day and report an update', async () => {
      checkForUpdate.mockResolvedValue({ updateAvailable: true, versions: { local: 5, newChanges: 3, remote: 42 } });

      const result = await useAssetUpdateSteps().checkUpdate();

      expect(checkForUpdate).toHaveBeenCalledTimes(1);
      expect(result).toEqual({ ok: true, value: { some: true, value: { changes: 3, local: 5, remote: 42, upToVersion: 42 } } });
    });

    it('should skip the check entirely when the per-run skip_update flag is set', async () => {
      sessionStorage.setItem('skip_update', '1');

      const result = await useAssetUpdateSteps().checkUpdate();

      expect(checkForUpdate).not.toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: { some: false } });
    });

    it('should report no update when the remote version was permanently skipped', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '42');
      checkForUpdate.mockResolvedValue({ updateAvailable: true, versions: { local: 5, newChanges: 3, remote: 42 } });

      const result = await useAssetUpdateSteps().checkUpdate();

      expect(result).toEqual({ ok: true, value: { some: false } });
    });

    it('should report no update when none is available', async () => {
      checkForUpdate.mockResolvedValue({ updateAvailable: false, versions: undefined });

      const result = await useAssetUpdateSteps().checkUpdate();

      expect(result).toEqual({ ok: true, value: { some: false } });
    });

    it('should skip the network on a second check the same day/version', async () => {
      checkForUpdate.mockResolvedValue({ updateAvailable: false, versions: undefined });

      const steps = useAssetUpdateSteps();
      await steps.checkUpdate();
      checkForUpdate.mockClear();
      const result = await steps.checkUpdate();

      expect(checkForUpdate).not.toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: { some: false } });
    });
  });

  describe('applyUpdate', () => {
    it('should map a completed update to done', async () => {
      applyUpdates.mockResolvedValue({ done: true });

      const result = await useAssetUpdateSteps().applyUpdate(42);

      expect(applyUpdates).toHaveBeenCalledWith({ resolution: undefined, version: 42 });
      expect(result).toEqual({ ok: true, value: { kind: 'done' } });
    });

    it('should map conflicts to the conflicts outcome', async () => {
      const conflicts = [{ identifier: 'a' }];
      applyUpdates.mockResolvedValue({ conflicts });

      const result = await useAssetUpdateSteps().applyUpdate(42);

      expect(result).toEqual({ ok: true, value: { conflicts, kind: 'conflicts' } });
    });

    it('should map a non-completing update to an updateFailed err', async () => {
      applyUpdates.mockResolvedValue({});

      const result = await useAssetUpdateSteps().applyUpdate(42);

      expect(result.ok).toBe(false);
    });
  });

  describe('requestRestart', () => {
    it('should ask for a restart without deciding whether one is possible', async () => {
      // The runtime check moved into restartBackend, which drives Electron, the
      // docker control endpoint, or nothing at all. Guarding again here is what
      // kept docker on the old silent no-op.
      restartBackend.mockResolvedValue({ status: BackendRestartStatus.restarted });

      const result = await useAssetUpdateSteps().requestRestart();

      expect(restartBackend).toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: undefined });
    });

    it('should restart the managed backend on Electron (packaged)', async () => {
      interopState.isPackaged = true;
      restartBackend.mockResolvedValue({ status: BackendRestartStatus.restarted });

      const result = await useAssetUpdateSteps().requestRestart();

      expect(restartBackend).toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: undefined });
    });

    /**
     * The update is already written to the global database by this point, so carrying on
     * would unlock a backend still holding the assets it was told to reload, and report
     * success for it. A refused restart has to stop the flow.
     */
    it('should fail the step when the restart is refused', async () => {
      restartBackend.mockResolvedValue({
        message: 'authentication required',
        status: BackendRestartStatus.failed,
      });

      const result = await useAssetUpdateSteps().requestRestart();

      expect(result).toEqual({ error: { kind: UnlockErrorKind.restartFailed }, ok: false });
    });

    // Not a failure: no runtime could restart anything, which is how the plain web build
    // has always behaved, so the unlock has to continue rather than block login.
    it('should continue when no runtime can restart at all', async () => {
      restartBackend.mockResolvedValue({ status: BackendRestartStatus.unavailable });

      const result = await useAssetUpdateSteps().requestRestart();

      expect(result).toEqual({ ok: true, value: undefined });
    });
  });
});
