import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { api } from '@/modules/core/api/rotki-api';
import { useSync } from '@/modules/session/use-session-sync';
import { SUGGESTION_PROBE_TAG } from '@/modules/settings/suggestions/use-suggestion-probes';
import { resetState } from '@/modules/shell/app/store-plugins';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorService();
  const orchestrator = useTaskOrchestrator();

  function cleanup(): void {
    clearUploadStatus();
    // Suggestion probes are fired at login and not awaited by it, so on a quick logout they can
    // still be queued against the session that just ended.
    api.cancelByTag(SUGGESTION_PROBE_TAG);
    // Drop native activities and the completion ledger so freshness/liveness never leak across
    // users (the orchestrator is app-scoped, not a pinia store reset by resetState).
    orchestrator.reset();
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
