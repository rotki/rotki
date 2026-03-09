import { useSync } from '@/composables/session/sync';
import { useMonitorService } from '@/modules/app/use-monitor-service';
import { BalanceQueueService } from '@/modules/balances/services/balance-queue';
import { resetState } from '@/store/plugins';
import { useSessionAuthStore } from '@/store/session/auth';

export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorService();

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
