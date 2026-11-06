import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const { fetchBalances, fetchNetValue, getPath, importBalancesSnapshot, logout, notifyInfo, uploadBalancesSnapshot } = vi.hoisted(() => ({
  fetchBalances: vi.fn(),
  fetchNetValue: vi.fn(),
  getPath: vi.fn(),
  importBalancesSnapshot: vi.fn(),
  logout: vi.fn(),
  notifyInfo: vi.fn<(title: string, message: string) => void>(),
  uploadBalancesSnapshot: vi.fn(),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: (): { fetchBalances: typeof fetchBalances } => ({ fetchBalances }),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: (): { fetchNetValue: typeof fetchNetValue } => ({ fetchNetValue }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): { notifyInfo: typeof notifyInfo } => ({ notifyInfo }),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): { logout: typeof logout } => ({ logout }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>({ getPath }),
}));

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: (): { importBalancesSnapshot: typeof importBalancesSnapshot; uploadBalancesSnapshot: typeof uploadBalancesSnapshot } => ({
    importBalancesSnapshot,
    uploadBalancesSnapshot,
  }),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    logout.mockResolvedValue(undefined);
    getPath.mockReturnValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('forceSave', () => {
    it('should refetch balances ignoring the cache and persist a snapshot', async () => {
      const { forceSave } = withSetup(() => useSnapshotActions()).result;

      await forceSave();

      expect(fetchBalances).toHaveBeenCalledWith({ ignoreCache: true, saveData: true });
      expect(fetchNetValue).toHaveBeenCalledOnce();
    });

    it('should pass ignoreErrors when the frontend setting is enabled', async () => {
      useSettingsRepo().updateFrontend({ ignoreSnapshotError: true });
      const { forceSave } = withSetup(() => useSnapshotActions()).result;

      await forceSave();

      expect(fetchBalances).toHaveBeenCalledWith({ ignoreCache: true, ignoreErrors: true, saveData: true });
    });

    it('should toggle the saving flag around the operation', async () => {
      const { forceSave, forceSaving } = withSetup(() => useSnapshotActions()).result;
      expect(get(forceSaving)).toBe(false);

      const promise = forceSave();
      expect(get(forceSaving)).toBe(true);

      await promise;
      expect(get(forceSaving)).toBe(false);
    });
  });

  describe('importSnapshot', () => {
    it('should do nothing when both files are not set', async () => {
      const { modelBalanceFile, importSnapshot } = withSetup(() => useSnapshotActions()).result;
      set(modelBalanceFile, new File([], 'balances.csv'));
      // location file left unset

      await importSnapshot();

      expect(uploadBalancesSnapshot).not.toHaveBeenCalled();
      expect(importBalancesSnapshot).not.toHaveBeenCalled();
    });

    it('should upload the files and log out on success (web path)', async () => {
      vi.useFakeTimers();
      uploadBalancesSnapshot.mockResolvedValue(undefined);
      const { modelBalanceFile, importSnapshot, modelLocationFile } = withSetup(() => useSnapshotActions()).result;
      const balance = new File([], 'balances.csv');
      const location = new File([], 'locations.csv');
      set(modelBalanceFile, balance);
      set(modelLocationFile, location);

      await importSnapshot();

      expect(uploadBalancesSnapshot).toHaveBeenCalledWith(balance, location);
      expect(notifyInfo).toHaveBeenCalledExactlyOnceWith(
        'snapshot_action_button.messages.title',
        'snapshot_action_button.messages.success_description',
      );
      // Files are cleared so a stale selection can't be re-imported.
      expect(get(modelBalanceFile)).toBeUndefined();
      expect(get(modelLocationFile)).toBeUndefined();

      // Logout is deferred so the success message is seen first.
      expect(logout).not.toHaveBeenCalled();
      vi.advanceTimersByTime(3000);
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should import by path when running in electron', async () => {
      vi.useFakeTimers();
      getPath.mockImplementation((file: File) => `/tmp/${file.name}`);
      importBalancesSnapshot.mockResolvedValue(undefined);
      const { modelBalanceFile, importSnapshot, modelLocationFile } = withSetup(() => useSnapshotActions()).result;
      set(modelBalanceFile, new File([], 'balances.csv'));
      set(modelLocationFile, new File([], 'locations.csv'));

      await importSnapshot();

      expect(importBalancesSnapshot).toHaveBeenCalledWith('/tmp/balances.csv', '/tmp/locations.csv');
      expect(uploadBalancesSnapshot).not.toHaveBeenCalled();
    });

    it('should expose the failure for the dialog and not log out when the import throws', async () => {
      vi.useFakeTimers();
      uploadBalancesSnapshot.mockRejectedValue(new Error('boom'));
      const { modelBalanceFile, modelImportFailure, importSnapshot, modelLocationFile } = withSetup(() => useSnapshotActions()).result;
      set(modelBalanceFile, new File([], 'balances.csv'));
      set(modelLocationFile, new File([], 'locations.csv'));

      await importSnapshot();

      expect(get(modelImportFailure)).toBe('boom');
      expect(notifyInfo).not.toHaveBeenCalled();
      vi.advanceTimersByTime(3000);
      expect(logout).not.toHaveBeenCalled();
    });

    it('should keep both chosen files after a failed import so a retry needs no re-picking', async () => {
      uploadBalancesSnapshot.mockRejectedValue(new Error('boom'));
      const { modelBalanceFile, importSnapshot, modelLocationFile } = withSetup(() => useSnapshotActions()).result;
      const balance = new File([], 'balances.csv');
      const location = new File([], 'locations.csv');
      set(modelBalanceFile, balance);
      set(modelLocationFile, location);

      await importSnapshot();

      expect(get(modelBalanceFile)).toBe(balance);
      expect(get(modelLocationFile)).toBe(location);
    });

    it('should clear the failure when the next import starts', async () => {
      vi.useFakeTimers();
      uploadBalancesSnapshot.mockRejectedValueOnce(new Error('boom'));
      let finish: () => void = () => {};
      uploadBalancesSnapshot.mockReturnValueOnce(new Promise<void>((resolve) => {
        finish = resolve;
      }));
      const { modelBalanceFile, modelImportFailure, importSnapshot, modelLocationFile } = withSetup(() => useSnapshotActions()).result;
      set(modelBalanceFile, new File([], 'balances.csv'));
      set(modelLocationFile, new File([], 'locations.csv'));

      await importSnapshot();
      const retry = importSnapshot();

      expect(get(modelImportFailure)).toBeUndefined();
      finish();
      await retry;
    });
  });
});
