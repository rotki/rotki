import { startPromise } from '@shared/utils';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { logger } from '@/modules/core/common/logging/logging';
import { useMonitorWatchers } from '@/modules/shell/sync-progress/use-monitor-watchers';
import { useBalanceRefreshScheduler } from './schedulers/use-balance-refresh-scheduler';
import { useEvmStatusScheduler } from './schedulers/use-evm-status-scheduler';
import { usePasswordCheckScheduler } from './schedulers/use-password-check-scheduler';
import { usePeriodicPollingScheduler } from './schedulers/use-periodic-polling-scheduler';
import { useTaskPollingScheduler } from './schedulers/use-task-polling-scheduler';
import { useWebsocketConnection } from './use-websocket-connection';

interface UseMonitorServiceInternalReturn {
  restart: () => void;
  start: (restarting?: boolean) => void;
  startTaskMonitoring: (restarting: boolean) => void;
  stop: () => void;
}

function useMonitorServiceInternal(): UseMonitorServiceInternalReturn {
  const { connect, disconnect } = useWebsocketConnection();

  const taskScheduler = useTaskPollingScheduler();
  const periodicScheduler = usePeriodicPollingScheduler();
  const balanceScheduler = useBalanceRefreshScheduler();
  const evmStatusScheduler = useEvmStatusScheduler();
  const passwordCheckScheduler = usePasswordCheckScheduler();

  useMonitorWatchers();
  useTokenDetectionOrchestrator();

  const schedulers = [taskScheduler, periodicScheduler, balanceScheduler, evmStatusScheduler, passwordCheckScheduler];

  const connectWebSocket = async (restarting: boolean): Promise<void> => {
    try {
      await connect();
      periodicScheduler.start(!restarting);
    }
    catch (error: unknown) {
      logger.error(error);
    }
  };

  const startTaskMonitoring = (restarting: boolean): void => {
    taskScheduler.start(!restarting);
  };

  const start = function (restarting = false): void {
    startPromise(connectWebSocket(restarting));
    startTaskMonitoring(restarting);
    balanceScheduler.start();
    evmStatusScheduler.start();
    passwordCheckScheduler.start();
  };

  const stop = (): void => {
    disconnect();
    for (const scheduler of schedulers)
      scheduler.stop();
  };

  const restart = (): void => {
    stop();
    start(true);
  };

  onScopeDispose(() => {
    stop();
  });

  return {
    restart,
    start,
    startTaskMonitoring,
    stop,
  };
}

export const useMonitorService = createGlobalState(useMonitorServiceInternal);
