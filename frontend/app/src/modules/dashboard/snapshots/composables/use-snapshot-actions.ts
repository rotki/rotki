import type { Ref } from 'vue';
import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { useLogout } from '@/modules/auth/use-logout';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { useSetting } from '@/modules/settings/use-setting';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

interface UseSnapshotActionsReturn {
  /** Whether a force-save (take snapshot) is in progress. */
  forceSaving: Readonly<Ref<boolean>>;
  /** Re-fetch every balance ignoring the cache and persist a fresh snapshot. */
  forceSave: () => Promise<void>;
  /** Whether a manual import is in progress. */
  importing: Readonly<Ref<boolean>>;
  /** The balance CSV the manual import will upload. */
  modelBalanceFile: Ref<File | undefined>;
  /** The location-data CSV the manual import will upload. */
  modelLocationFile: Ref<File | undefined>;
  /**
   * Why the last import failed, for the import dialog to name.
   *
   * @remarks
   * Cleared when the next import starts. Writable so the dialog can clear it when it closes.
   */
  modelImportFailure: Ref<string | undefined>;
  /**
   * Upload the chosen CSVs; on success a toast says the user is about to be logged out, and the
   * logout follows so the import takes effect.
   */
  importSnapshot: () => Promise<void>;
}

/**
 * The two snapshot-management actions shared by the dashboard menu and the
 * snapshots page: *force save* (take a fresh snapshot of all balances) and the
 * manual CSV *import*. Both have notable side effects: force save refetches
 * every balance (slow, rate-limit prone), and a successful import logs the user
 * out so it can be re-read on next login. So they live behind one composable
 * rather than being copy-pasted per call site.
 */
export function useSnapshotActions(): UseSnapshotActionsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const forceSaving = shallowRef<boolean>(false);
  const importing = shallowRef<boolean>(false);
  const modelBalanceFile = shallowRef<File>();
  const modelLocationFile = shallowRef<File>();
  const modelImportFailure = shallowRef<string>();
  let logoutTimer: ReturnType<typeof setTimeout> | undefined;

  const { logout } = useLogout();
  const { fetchBalances } = useBalanceFetching();
  const { fetchNetValue } = useStatisticsDataFetching();
  const { notifyInfo } = useNotifications();
  const { getPath } = useInterop();
  const { importBalancesSnapshot, uploadBalancesSnapshot } = useSnapshotApi();
  const ignoreSnapshotError = useSetting('ignoreSnapshotError');

  async function forceSave(): Promise<void> {
    set(forceSaving, true);
    try {
      const payload: Partial<AllBalancePayload> = {
        ignoreCache: true,
        saveData: true,
        ...(get(ignoreSnapshotError) ? { ignoreErrors: true } : {}),
      };

      await fetchBalances(payload);
      await fetchNetValue();
    }
    finally {
      set(forceSaving, false);
    }
  }

  async function importSnapshot(): Promise<void> {
    if (!(isDefined(modelBalanceFile) && isDefined(modelLocationFile)))
      return;

    set(importing, true);
    set(modelImportFailure, undefined);

    const balance = get(modelBalanceFile);
    const location = get(modelLocationFile);

    let success = false;
    try {
      // In Electron the files resolve to absolute paths; on web we upload them.
      const balancePath = getPath(balance);
      const locationPath = getPath(location);
      if (balancePath && locationPath)
        await importBalancesSnapshot(balancePath, locationPath);
      else
        await uploadBalancesSnapshot(balance, location);

      success = true;
    }
    catch (error: unknown) {
      set(modelImportFailure, getErrorMessage(error));
    }

    if (success) {
      notifyInfo(
        t('snapshot_action_button.messages.title'),
        t('snapshot_action_button.messages.success_description'),
      );
      // Let the success message land, then log out so the import is re-read on login.
      logoutTimer = setTimeout(() => {
        startPromise(logout());
      }, 3000);
    }

    set(importing, false);
    if (!success)
      return;

    set(modelBalanceFile, undefined);
    set(modelLocationFile, undefined);
  }

  // Cancel the pending logout if the caller unmounts before it fires.
  onScopeDispose(() => {
    if (logoutTimer)
      clearTimeout(logoutTimer);
  });

  return {
    forceSave,
    forceSaving: readonly(forceSaving),
    importing: readonly(importing),
    importSnapshot,
    modelBalanceFile,
    modelImportFailure,
    modelLocationFile,
  };
}
