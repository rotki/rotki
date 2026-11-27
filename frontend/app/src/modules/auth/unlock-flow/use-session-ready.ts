import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { lastLogin } from '@/modules/auth/account-management';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';

export interface UseSessionReadyReturn {
  handleSessionReady: () => Promise<void>;
}

/**
 * Runs the post-unlock side-effects shared by every unlock path.
 *
 * @remarks
 * Manual login, account creation and auto-login all funnel through `useUnlockFlowController`,
 * which calls this once the flow reaches `ready`. Add a shared effect here rather than at a call
 * site, where it would run in a different order on each path; path-specific effects belong on the
 * controller's per-mode hooks.
 */
export function useSessionReady(): UseSessionReadyReturn {
  const authStore = useSessionAuthStore();
  const { canRequestData, username } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { showGetPremiumButton } = usePremiumHelper();
  const { fetchTransactionStatusSummary } = useHistoryDataFetching();
  const { navigateAfterUnlock } = useAppNavigation();
  const { showReleaseNotes } = useUpdateMessage();
  const { refreshSupportedChains } = useSupportedChains();

  /**
   * @remarks
   * The upgrade state is cleared only once the app has navigated away: clearing it first takes the
   * finished upgrade screen down while the session data still loads, and the login form flashes back
   * in its place.
   */
  async function handleSessionReady(): Promise<void> {
    set(canRequestData, true);
    set(lastLogin, get(username));
    showGetPremiumButton();
    try {
      await refreshSupportedChains();
      await fetchTransactionStatusSummary();
      await navigateAfterUnlock();
    }
    finally {
      clearUpgradeMessages();
    }
    set(showReleaseNotes, false);
  }

  return { handleSessionReady };
}
