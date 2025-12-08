import { useSync } from '@/composables/session/sync';
import { BalanceQueueService } from '@/services/balance-queue';
import { useMonitorStore } from '@/store/monitor';
import { resetState } from '@/store/plugins';
import { useSessionAuthStore } from '@/store/session/auth';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorStore();

  function cleanup(): void {
    clearUploadStatus();
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
