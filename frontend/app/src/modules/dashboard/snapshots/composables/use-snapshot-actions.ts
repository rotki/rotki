import type { Ref } from 'vue';
import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { useLogout } from '@/modules/auth/use-logout';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
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
  /** Upload the chosen CSVs; on success the user is logged out so the import takes effect. */
  importSnapshot: () => Promise<void>;
}

/**
 * The two snapshot-management actions shared by the dashboard menu and the
 * snapshots page: *force save* (take a fresh snapshot of all balances) and the
 * manual CSV *import*. Both have notable side effects — force save refetches
 * every balance (slow, rate-limit prone), and a successful import logs the user
 * out so it can be re-read on next login — so they live behind one composable
 * rather than being copy-pasted per call site.
 */
export function useSnapshotActions(): UseSnapshotActionsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const forceSaving = shallowRef<boolean>(false);
  const importing = shallowRef<boolean>(false);
  const modelBalanceFile = shallowRef<File>();
  const modelLocationFile = shallowRef<File>();
  let logoutTimer: ReturnType<typeof setTimeout> | undefined;

  const { logout } = useLogout();
  const { fetchBalances } = useBalanceFetching();
  const { fetchNetValue } = useStatisticsDataFetching();
  const { setMessage } = useMessageStore();
  const { getPath } = useInterop();
  const { importBalancesSnapshot, uploadBalancesSnapshot } = useSnapshotApi();
  const { ignoreSnapshotError } = storeToRefs(useFrontendSettingsStore());

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

    const balance = get(modelBalanceFile);
    const location = get(modelLocationFile);

    let success = false;
    let message = '';
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
      message = getErrorMessage(error);
    }

    if (success) {
      setMessage({
        description: t('snapshot_action_button.messages.success_description', { message }),
        success: true,
        title: t('snapshot_action_button.messages.title'),
      });
      // Let the success message land, then log out so the import is re-read on login.
      logoutTimer = setTimeout(() => {
        startPromise(logout());
      }, 3000);
    }
    else {
      setMessage({
        description: t('snapshot_action_button.messages.failed_description', { message }),
        title: t('snapshot_action_button.messages.title'),
      });
    }

    set(importing, false);
    set(modelBalanceFile, undefined);
    set(modelLocationFile, undefined);
  }

  // Cancel the pending logout if the caller unmounts before it fires.
  onScopeDispose(() => {
    if (logoutTimer)
      clearTimeout(logoutTimer);
  });

  return {
    // model* refs are bound via v-model by the import dialog's file pickers,
    // so they stay writable (the `model` prefix exempts them from readonly()).
    forceSave,
    forceSaving: readonly(forceSaving),
    importing: readonly(importing),
    importSnapshot,
    modelBalanceFile,
    modelLocationFile,
  };
}
