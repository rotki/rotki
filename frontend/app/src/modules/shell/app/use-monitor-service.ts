import { startPromise } from '@shared/utils';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { logger } from '@/modules/core/common/logging/logging';
import { onSessionEnd } from '@/modules/core/session/session-lifecycle';
import { useMonitorWatchers } from '@/modules/shell/app/use-monitor-watchers';
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
  const { connect, disconnect, setConnectionEnabled } = useWebsocketConnection();

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
    setConnectionEnabled(true);
    startPromise(connectWebSocket(restarting));
    startTaskMonitoring(restarting);
    balanceScheduler.start();
    evmStatusScheduler.start();
    passwordCheckScheduler.start();
  };

  const stop = (): void => {
    setConnectionEnabled(false);
    disconnect();
    for (const scheduler of schedulers)
      scheduler.stop();
  };

  const restart = (): void => {
    stop();
    start(true);
  };

  const stopOnSessionEnd = onSessionEnd('monitor-service', stop);

  onScopeDispose(() => {
    stopOnSessionEnd();
    stop();
  });

  return {
    restart,
    start,
    startTaskMonitoring,
    stop,
  };
}

/**
 * The websocket and the session's pollers, started by the unlock flow.
 *
 * @remarks
 * Stops when the session ends. Every poller reads data that belongs to the session, so one still
 * ticking on the login screen only reaches a backend that refuses it.
 */
export const useMonitorService = createGlobalState(useMonitorServiceInternal);
