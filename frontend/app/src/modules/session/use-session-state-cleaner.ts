import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { api } from '@/modules/core/api/rotki-api';
import { useSync } from '@/modules/session/use-session-sync';
import { SUGGESTION_PROBE_TAG } from '@/modules/settings/suggestions/use-suggestion-probes';
import { resetState } from '@/modules/shell/app/store-plugins';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorService();
  const orchestrator = useTaskOrchestrator();
  const { reset: resetNativeTasks } = useNativeTask();
  const { reset: resetAccountLoad } = useAccountLoadState();
  const { reset: resetHydration } = useBalanceHydration();

  function cleanup(): void {
    clearUploadStatus();
    // Suggestion probes are fired at login and not awaited by it, so on a quick logout they can
    // still be queued against the session that just ended.
    api.cancelByTag(SUGGESTION_PROBE_TAG);
    // Drop native activities and the completion ledger so freshness/liveness never leak across
    // users (the orchestrator is app-scoped, not a pinia store reset by resetState).
    orchestrator.reset();
    // After the orchestrator, so its emit gets the chance to settle each caller normally and this
    // only sweeps up what that missed. An id left in the submission map outlives the session and
    // `submitTask` dedups by id, so the next session joins a promise that can never resolve — how
    // `prices:exchange-rates` stalled `fetchCached` on its first await after a re-login, leaving
    // the new session with no exchange rates, no accounts and no balances.
    resetNativeTasks();
    // Same reason, same scope: a read tracked here outlives the session that started it.
    resetAccountLoad();
    // Hydration dedups by chain against an app-scoped map, so a read that can never settle (its
    // backend task belonged to the session that just ended) would be handed to the next session's
    // caller for that chain — which then never hydrates, silently.
    resetHydration();
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
