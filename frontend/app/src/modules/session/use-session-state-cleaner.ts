import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { endSession, onSessionCleared, onSessionEnd, scheduleSessionClear } from '@/modules/core/session/session-lifecycle';
import { useSync } from '@/modules/session/use-session-sync';
import { resetState } from '@/modules/shell/app/store-plugins';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/**
 * Ties the app-wide parts of a session to its lifecycle: the monitors start on login, and when the
 * session ends its work stops and the state it leaves is cleared.
 *
 * @remarks
 * The orchestrator, the submission map, the account-load tracker and the hydration map are all
 * app-scoped. Anything they still hold at logout outlives the session, and because each dedups by
 * identity, the *next* session is handed work that can never settle: a promise nothing resolves,
 * or a read belonging to a user who is gone.
 *
 * The work stops when the session ends, and `resetNativeTasks` runs after the orchestrator so its
 * emit can settle each caller normally and this only sweeps what that missed. The stores are reset
 * in the clear phase, after the callers those resets settled have resumed and written whatever
 * they write, so none of it reaches the next session.
 */
export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorService();
  const orchestrator = useTaskOrchestrator();
  const { reset: resetNativeTasks } = useNativeTask();
  const { reset: resetAccountLoad } = useAccountLoadState();
  const { reset: resetHydration } = useBalanceHydration();

  onSessionEnd('session-work', () => {
    stop();
    orchestrator.reset();
    resetNativeTasks();
    resetAccountLoad();
    resetHydration();
  });

  onSessionCleared('session-state', () => {
    clearUploadStatus();
    resetState();
  });

  /**
   * Starts the monitors on login; on any logout, ends the session and schedules its clear phase.
   *
   * @remarks
   * `logout()` has already ended the session by then. Ending it here as well covers the paths
   * that drop `logged` without one, such as a 401 while logged in.
   */
  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged)
        start();

      return;
    }
    endSession();
    scheduleSessionClear();
  });
}
