import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { BalanceQueueService } from '@/modules/balances/services/balance-queue';
import { api } from '@/modules/core/api/rotki-api';
import { useSync } from '@/modules/session/use-session-sync';
import { SUGGESTION_PROBE_TAG } from '@/modules/settings/suggestions/use-suggestion-probes';
import { resetState } from '@/modules/shell/app/store-plugins';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorService();

  function cleanup(): void {
    clearUploadStatus();
    // Suggestion probes are fired at login and not awaited by it, so on a quick logout they can
    // still be queued against the session that just ended.
    api.cancelByTag(SUGGESTION_PROBE_TAG);
    BalanceQueueService.resetInstance();
    resetState();
  }

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged)
        start();

      return;
    }
    stop();
    cleanup();
  });
}
