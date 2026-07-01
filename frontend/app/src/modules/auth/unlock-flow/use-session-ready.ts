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
 * The shared post-unlock side-effects. Every unlock path (manual login, account
 * creation, auto-login/resume) funnels through `useUnlockFlowController`, which calls
 * this once the flow reaches `ready`. Centralizing them here removes the duplication
 * (and the ordering race) that previously lived across `use-account-management`, the
 * login page `watch(logged)`, and `use-auto-login`. Path-specific effects stay at the
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

  async function handleSessionReady(): Promise<void> {
    clearUpgradeMessages();
    set(canRequestData, true);
    set(lastLogin, get(username));
    showGetPremiumButton();
    // Load the supported chains before navigating: dashboard/accounts consumers read
    // the chain list imperatively, so it must be populated before the destination mounts.
    // Runs here (post-unlock) so the calls never fire on the login screen.
    await refreshSupportedChains();
    await fetchTransactionStatusSummary();
    await navigateToDashboard();
    set(showReleaseNotes, false);
  }

  return { handleSessionReady };
}
