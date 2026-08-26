import { startPromise } from '@shared/utils';
import { lastLogin } from '@/modules/auth/account-management';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useGnosisPaySafeMigration } from '@/modules/integrations/gnosis-pay/use-gnosis-pay-safe-migration';
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
  const { navigateToDashboard } = useAppNavigation();
  const { showReleaseNotes } = useUpdateMessage();
  const { refreshSupportedChains } = useSupportedChains();
  const { checkAndNotify: checkGnosisPaySafeMigration } = useGnosisPaySafeMigration();

  async function handleSessionReady(): Promise<void> {
    clearUpgradeMessages();
    set(canRequestData, true);
    set(lastLogin, get(username));
    showGetPremiumButton();
    await refreshSupportedChains();
    await fetchTransactionStatusSummary();
    await navigateToDashboard();
    set(showReleaseNotes, false);
    // Fire-and-forget: a premium-gated network check that must not block navigation.
    startPromise(checkGnosisPaySafeMigration());
  }

  return { handleSessionReady };
}
