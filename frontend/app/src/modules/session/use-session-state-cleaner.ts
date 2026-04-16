import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { BalanceQueueService } from '@/modules/balances/services/balance-queue';
import { useSync } from '@/modules/session/use-session-sync';
import { resetState } from '@/modules/shell/app/store-plugins';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';

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
