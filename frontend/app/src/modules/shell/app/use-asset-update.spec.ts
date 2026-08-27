import type { ApplyUpdateResult, AssetUpdateCheckResult, AssetUpdateConflictResult } from '@/modules/assets/types';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { useAssetUpdate } from './use-asset-update';

const {
  applyUpdates,
  checkForUpdate,
  reload,
  restarting,
  setMessage,
  show,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    applyUpdates: vi.fn(),
    checkForUpdate: vi.fn(),
    reload: vi.fn(),
    restarting: ref<boolean>(false),
    setMessage: vi.fn(),
    show: vi.fn(),
  };
});

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: (): Record<string, unknown> => ({ applyUpdates, checkForUpdate }),
}));

vi.mock('@/modules/shell/app/use-backend-reload', () => ({
  useBackendReload: (): Record<string, unknown> => ({ reload }),
}));

vi.mock('@/modules/auth/use-restarting-status', () => ({
  useRestartingStatus: (): Record<string, unknown> => ({ restarting }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

const wrappers: VueWrapper[] = [];
const onSkip = vi.fn();

function conflict(identifier: string): AssetUpdateConflictResult {
  return createMock<AssetUpdateConflictResult>({ identifier });
}

function checkReturns(result: Partial<AssetUpdateCheckResult>): void {
  checkForUpdate.mockResolvedValue({ updateAvailable: false, ...result });
}

function applyReturns(result: Partial<ApplyUpdateResult>): void {
  applyUpdates.mockResolvedValue({ done: true, ...result });
}

function mountUpdate(headless = false): ReturnType<typeof useAssetUpdate> {
  let captured: ReturnType<typeof useAssetUpdate> | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useAssetUpdate({ headless: () => headless, onSkip });
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  if (setupError)
    throw setupError;
  return captured!;
}

describe('modules/shell/app/useAssetUpdate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    set(restarting, false);
    checkReturns({});
    applyReturns({});
    reload.mockResolvedValue(undefined);
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('what happens on mount', () => {
    it('should not check when the app asked for the update to be skipped this run', async () => {
      sessionStorage.setItem('skip_update', 'true');

      mountUpdate(true);
      await flushPromises();

      expect(checkForUpdate).not.toHaveBeenCalled();
      expect(onSkip).toHaveBeenCalledOnce();
    });

    it('should check straight away when it owns the screen', async () => {
      mountUpdate(true);
      await flushPromises();

      expect(checkForUpdate).toHaveBeenCalledOnce();
    });

    it('should wait to be asked when it is only a settings row', async () => {
      mountUpdate(false);
      await flushPromises();

      expect(checkForUpdate).not.toHaveBeenCalled();
    });
  });

  describe('the version check', () => {
    it('should open the prompt when an update exists', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, showUpdateDialog } = mountUpdate();

      await check();

      expect(get(showUpdateDialog)).toBe(true);
    });

    it('should target the remote version it was told about', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, modelChanges } = mountUpdate();

      await check();

      expect(get(modelChanges)).toEqual({ changes: 5, local: 1, remote: 2, upToVersion: 2 });
    });

    it('should tell a settings user there was nothing to do', async () => {
      const { check } = mountUpdate(false);

      await check();

      expect(setMessage).toHaveBeenCalledOnce();
      expect(onSkip).not.toHaveBeenCalled();
    });

    it('should move the app on rather than message when it owns the screen', async () => {
      const { check } = mountUpdate(true);
      await flushPromises();
      onSkip.mockClear();

      await check();

      expect(onSkip).toHaveBeenCalledOnce();
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should not offer a version the user already skipped', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '2');
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, showUpdateDialog } = mountUpdate(true);
      await flushPromises();
      onSkip.mockClear();

      await check();

      expect(get(showUpdateDialog)).toBe(false);
      expect(onSkip).toHaveBeenCalledOnce();
    });

    it('should still offer a newer version than the one skipped', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '2');
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 3 } });
      const { check, showUpdateDialog } = mountUpdate(true);

      await check();

      expect(get(showUpdateDialog)).toBe(true);
    });

    it('should offer a skipped version again in the settings, where the user asked for it', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '2');
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, showUpdateDialog } = mountUpdate(false);

      await check();

      expect(get(showUpdateDialog)).toBe(true);
    });

    it('should report it is checking only while the check is in flight', async () => {
      let release: (result: AssetUpdateCheckResult) => void = () => {};
      checkForUpdate.mockReturnValue(new Promise((resolve) => {
        release = resolve;
      }));
      const { check, status } = mountUpdate();

      const pending = check();
      expect(get(status)).toBe('checking');

      release({ updateAvailable: false });
      await pending;
      expect(get(status)).toBeNull();
    });
  });

  describe('skipping', () => {
    it('should close both prompts and move the app on', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, modelShowConflictDialog, showUpdateDialog, skip } = mountUpdate();
      await check();

      skip(false);

      expect(get(showUpdateDialog)).toBe(false);
      expect(get(modelShowConflictDialog)).toBe(false);
      expect(onSkip).toHaveBeenCalledOnce();
    });

    it('should remember the version only when the user asked to skip it', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 2 } });
      const { check, skip, skipped } = mountUpdate();
      await check();

      skip(false);
      expect(get(skipped)).toBe(0);

      skip(true);
      expect(get(skipped)).toBe(2);
    });

    it('should remember the remote version, not the one being updated to', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 7 } });
      const { check, modelChanges, skip, skipped } = mountUpdate();
      await check();
      set(modelChanges, { ...get(modelChanges), upToVersion: 4 });

      skip(true);

      expect(get(skipped)).toBe(7);
    });
  });

  describe('applying the update', () => {
    it('should apply up to the targeted version', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 3 } });
      const { check, updateAssets } = mountUpdate();
      await check();

      await updateAssets();

      expect(applyUpdates).toHaveBeenCalledExactlyOnceWith({ resolution: undefined, version: 3 });
    });

    it('should pass the resolution the user chose', async () => {
      const { updateAssets } = mountUpdate();

      await updateAssets({ ETH: 'local' });

      expect(applyUpdates).toHaveBeenCalledWith({ resolution: { ETH: 'local' }, version: 0 });
    });

    it('should close the prompt before writing anything', async () => {
      checkReturns({ updateAvailable: true, versions: { local: 1, newChanges: 5, remote: 3 } });
      const { check, showUpdateDialog, updateAssets } = mountUpdate();
      await check();

      await updateAssets();

      expect(get(showUpdateDialog)).toBe(false);
    });

    it('should report it is applying only while the write is in flight', async () => {
      let release: (result: ApplyUpdateResult) => void = () => {};
      applyUpdates.mockReturnValue(new Promise((resolve) => {
        release = resolve;
      }));
      const { status, updateAssets } = mountUpdate();

      const pending = updateAssets();
      expect(get(status)).toBe('applying');

      release({ done: true });
      await pending;
      expect(get(status)).toBeNull();
    });

    it('should clear the skipped version once the update the user avoided has happened', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '2');
      const { skipped, updateAssets } = mountUpdate();

      await updateAssets();

      expect(get(skipped)).toBe(0);
    });
  });

  describe('a conflicting update', () => {
    it('should surface the conflicts for resolution rather than reporting success', async () => {
      applyReturns({ conflicts: [conflict('ETH')], done: false });
      const { conflicts, modelShowConflictDialog, updateAssets } = mountUpdate();

      await updateAssets();

      expect(get(modelShowConflictDialog)).toBe(true);
      expect(get(conflicts)).toHaveLength(1);
      expect(show).not.toHaveBeenCalled();
    });

    it('should not open the conflict dialog when the backend reported none', async () => {
      applyReturns({ done: false });
      const { modelShowConflictDialog, updateAssets } = mountUpdate();

      await updateAssets();

      expect(get(modelShowConflictDialog)).toBe(false);
    });

    it('should leave the skipped version alone when the update did not land', async () => {
      localStorage.setItem('rotki_skip_asset_db_version', '2');
      applyReturns({ conflicts: [conflict('ETH')], done: false });
      const { skipped, updateAssets } = mountUpdate();

      await updateAssets();

      expect(get(skipped)).toBe(2);
    });
  });

  describe('confirming a finished update', () => {
    it('should ask a settings user to confirm before restarting', async () => {
      const { updateAssets } = mountUpdate(false);

      await updateAssets();

      expect(show).toHaveBeenCalledOnce();
      expect(reload).not.toHaveBeenCalled();
    });

    it('should restart once that confirmation is accepted', async () => {
      const { updateAssets } = mountUpdate(false);
      await updateAssets();

      await show.mock.calls[0][1]();

      expect(reload).toHaveBeenCalledOnce();
    });

    it('should confirm inline when it owns the screen, since there is no dialog host', async () => {
      const { inlineConfirm, updateAssets } = mountUpdate(true);

      await updateAssets();

      expect(get(inlineConfirm)).toBe(true);
      expect(show).not.toHaveBeenCalled();
    });
  });

  describe('the restart', () => {
    it('should reload the backend so the new assets are served', async () => {
      const { updateComplete } = mountUpdate();

      await updateComplete();

      expect(reload).toHaveBeenCalledOnce();
    });

    it('should not start a second restart while one is already running', async () => {
      set(restarting, true);
      const { updateComplete } = mountUpdate();

      await updateComplete();

      expect(reload).not.toHaveBeenCalled();
    });

    it('should clear the restarting flag even when the reload fails, so a retry is possible', async () => {
      reload.mockRejectedValue(new Error('backend down'));
      const { updateComplete } = mountUpdate();

      await expect(updateComplete()).rejects.toThrow('backend down');

      expect(get(restarting)).toBe(false);
    });
  });
});
