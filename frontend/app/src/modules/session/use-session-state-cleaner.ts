import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { BALANCE_HYDRATION_TAG } from '@/modules/balances/api/use-blockchain-balances-api';
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

  /**
   * Tears down everything a session leaves behind that a pinia reset does not reach.
   *
   * @remarks
   * The orchestrator, the submission map, the account-load tracker and the hydration map are all
   * app-scoped. Anything they still hold at logout outlives the session, and because each dedups by
   * identity, the *next* session is handed work that can never settle — a promise nothing resolves,
   * or a read belonging to a user who is gone.
   *
   * Order matters twice: `resetNativeTasks` runs after the orchestrator so its emit can settle each
   * caller normally and this only sweeps what that missed, and the hydration request is cancelled
   * before its map is cleared, since clearing first leaves nothing to cancel against.
   */
  function cleanup(): void {
    clearUploadStatus();
    api.cancelByTag(SUGGESTION_PROBE_TAG);
    orchestrator.reset();
    resetNativeTasks();
    resetAccountLoad();
    api.cancelByTag(BALANCE_HYDRATION_TAG);
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
