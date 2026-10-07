import { startPromise } from '@shared/utils';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { logger } from '@/modules/core/common/logging/logging';
import { useMonitorWatchers } from '@/modules/shell/app/use-monitor-watchers';
import { useBalanceRefreshScheduler } from './schedulers/use-balance-refresh-scheduler';
import { useEvmStatusScheduler } from './schedulers/use-evm-status-scheduler';
import { usePasswordCheckScheduler } from './schedulers/use-password-check-scheduler';
import { usePeriodicPollingScheduler } from './schedulers/use-periodic-polling-scheduler';
import { useTaskPollingScheduler } from './schedulers/use-task-polling-scheduler';
import { useWebsocketConnection } from './use-websocket-connection';

export interface SessionMonitor {
  /** Connects the websocket and starts the pollers; `restarting` skips the immediate first poll. */
  start: (restarting?: boolean) => void;
  stop: () => void;
}

/**
 * One session's monitor: the websocket connection, its pollers, and the watchers that react to the
 * session's state.
 *
 * @remarks
 * Built by the session host, inside a component setup, so everything it builds (`useI18n`
 * included) has the component instance it needs, and everything it starts is disposed with the
 * session. Callers start and stop it through `useMonitorService`.
 */
export function useSessionMonitor(): SessionMonitor {
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

  const start = (restarting = false): void => {
    setConnectionEnabled(true);
    startPromise(connectWebSocket(restarting));
    taskScheduler.start(!restarting);
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

  onScopeDispose(stop);

  return { start, stop };
}
