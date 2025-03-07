import { useSync } from '@/composables/session/sync';
import { useMonitorStore } from '@/store/monitor';
import { resetState } from '@/store/plugins';
import { useSessionAuthStore } from '@/store/session/auth';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorStore();

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged)
        start();

      return;
    }
    clearUploadStatus();
    stop();
    resetState();
  });
}
