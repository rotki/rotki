import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetUpdateSteps } from './use-asset-update-steps';

const { applyUpdates, checkForUpdate, interopState, restartBackend } = vi.hoisted(() => ({
  applyUpdates: vi.fn(),
  checkForUpdate: vi.fn(),
  interopState: { isPackaged: false },
  restartBackend: vi.fn(),
}));

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: vi.fn(() => ({ applyUpdates, checkForUpdate })),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
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
    it('should be a no-op on web (not packaged)', async () => {
      const result = await useAssetUpdateSteps().requestRestart();

      expect(restartBackend).not.toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: undefined });
    });

    it('should restart the managed backend on Electron (packaged)', async () => {
      interopState.isPackaged = true;

      const result = await useAssetUpdateSteps().requestRestart();

      expect(restartBackend).toHaveBeenCalled();
      expect(result).toEqual({ ok: true, value: undefined });
    });
  });
});
