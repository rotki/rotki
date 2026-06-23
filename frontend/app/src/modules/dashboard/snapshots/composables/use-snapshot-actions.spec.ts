import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

// Hoisted so the vi.mock factories can reference them even when a dependency
// (e.g. logging via use-electron-interop) is resolved during eager module init.
const { fetchBalances, fetchNetValue, getPath, importBalancesSnapshot, logout, setMessage, uploadBalancesSnapshot } = vi.hoisted(() => ({
  fetchBalances: vi.fn(),
  fetchNetValue: vi.fn(),
  getPath: vi.fn(),
  importBalancesSnapshot: vi.fn(),
  logout: vi.fn(),
  setMessage: vi.fn(),
  uploadBalancesSnapshot: vi.fn(),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: (): { fetchBalances: typeof fetchBalances } => ({ fetchBalances }),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: (): { fetchNetValue: typeof fetchNetValue } => ({ fetchNetValue }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): { setMessage: typeof setMessage } => ({ setMessage }),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): { logout: typeof logout } => ({ logout }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { getPath: typeof getPath } => ({ getPath }),
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
      const { forceSave } = useSnapshotActions();

      await forceSave();

      expect(fetchBalances).toHaveBeenCalledWith({ ignoreCache: true, saveData: true });
      expect(fetchNetValue).toHaveBeenCalledOnce();
    });

    it('should pass ignoreErrors when the frontend setting is enabled', async () => {
      useFrontendSettingsStore().update({ ignoreSnapshotError: true });
      const { forceSave } = useSnapshotActions();

      await forceSave();

      expect(fetchBalances).toHaveBeenCalledWith({ ignoreCache: true, ignoreErrors: true, saveData: true });
    });

    it('should toggle the saving flag around the operation', async () => {
      const { forceSave, forceSaving } = useSnapshotActions();
      expect(get(forceSaving)).toBe(false);

      const promise = forceSave();
      expect(get(forceSaving)).toBe(true);

      await promise;
      expect(get(forceSaving)).toBe(false);
    });
  });

  describe('importSnapshot', () => {
    it('should do nothing when both files are not set', async () => {
      const { modelBalanceFile, importSnapshot } = useSnapshotActions();
      set(modelBalanceFile, new File([], 'balances.csv'));
      // location file left unset

      await importSnapshot();

      expect(uploadBalancesSnapshot).not.toHaveBeenCalled();
      expect(importBalancesSnapshot).not.toHaveBeenCalled();
    });

    it('should upload the files and log out on success (web path)', async () => {
      vi.useFakeTimers();
      uploadBalancesSnapshot.mockResolvedValue(undefined);
      const { modelBalanceFile, importSnapshot, modelLocationFile } = useSnapshotActions();
      const balance = new File([], 'balances.csv');
      const location = new File([], 'locations.csv');
      set(modelBalanceFile, balance);
      set(modelLocationFile, location);

      await importSnapshot();

      expect(uploadBalancesSnapshot).toHaveBeenCalledWith(balance, location);
      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
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
      const { modelBalanceFile, importSnapshot, modelLocationFile } = useSnapshotActions();
      set(modelBalanceFile, new File([], 'balances.csv'));
      set(modelLocationFile, new File([], 'locations.csv'));

      await importSnapshot();

      expect(importBalancesSnapshot).toHaveBeenCalledWith('/tmp/balances.csv', '/tmp/locations.csv');
      expect(uploadBalancesSnapshot).not.toHaveBeenCalled();
    });

    it('should surface a failure message and not log out when the import throws', async () => {
      vi.useFakeTimers();
      uploadBalancesSnapshot.mockRejectedValue(new Error('boom'));
      const { modelBalanceFile, importSnapshot, modelLocationFile } = useSnapshotActions();
      set(modelBalanceFile, new File([], 'balances.csv'));
      set(modelLocationFile, new File([], 'locations.csv'));

      await importSnapshot();

      expect(setMessage).toHaveBeenCalledWith(expect.not.objectContaining({ success: true }));
      vi.advanceTimersByTime(3000);
      expect(logout).not.toHaveBeenCalled();
    });
  });
});
