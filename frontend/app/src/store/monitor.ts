import { startPromise } from '@shared/utils';
import { useBalances } from '@/composables/balances';
import { useMonitorWatchers } from '@/composables/monitor/use-monitor-watchers';
import { useAutoLogin } from '@/composables/user/account';
import { useMessageHandling } from '@/modules/messaging';
import { useTaskMonitor } from '@/modules/tasks/use-task-monitor';
import { useHistoryStore } from '@/store/history';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePeriodicStore } from '@/store/session/periodic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useWebsocketStore } from '@/store/websocket';
import { logger } from '@/utils/logging';

const MonitorKey = {
  BALANCES: 'balances',
  EVM_EVENTS_STATUS: 'evm_events_status',
  PASSWORD_CONFIRMATION: 'password_confirmation',
  PERIODIC: 'periodic',
  TASK: 'task',
} as const;

const TASK_POLLING_MS = 4_000;
const EVM_STATUS_POLLING_MS = 10 * 60 * 1_000;
const PASSWORD_CHECK_MS = 60 * 60 * 1_000;
const SECONDS_TO_MS = 1_000;
const MINUTES_TO_MS = 60 * 1_000;

export const useMonitorStore = defineStore('monitor', () => {
  const monitors: Record<string, NodeJS.Timeout> = {};

  const authStore = useSessionAuthStore();
  const { canRequestData, logged, username } = storeToRefs(authStore);
  const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
  const { check } = usePeriodicStore();
  const { consume } = useMessageHandling();
  const { monitor } = useTaskMonitor();
  const { autoRefresh } = useBalances();
  const { fetchTransactionStatusSummary } = useHistoryStore();

  const frontendStore = useFrontendSettingsStore();
  const { queryPeriod, refreshPeriod } = storeToRefs(frontendStore);

  const ws = useWebsocketStore();
  const { connected } = storeToRefs(ws);
  const { connect, disconnect } = ws;

  useMonitorWatchers();

  const fetch = (): void => {
    if (get(canRequestData))
      startPromise(check());

    if (!get(connected))
      startPromise(consume());
  };

  const connectWebSocket = async (restarting: boolean): Promise<void> => {
    try {
      await connect();
      if (!monitors[MonitorKey.PERIODIC]) {
        if (!restarting)
          fetch();

        monitors[MonitorKey.PERIODIC] = setInterval(fetch, get(queryPeriod) * SECONDS_TO_MS);
      }
    }
    catch (error: unknown) {
      logger.error(error);
    }
  };

  const startTaskMonitoring = (restarting: boolean): void => {
    if (!monitors[MonitorKey.TASK]) {
      if (!restarting)
        startPromise(monitor());

      monitors[MonitorKey.TASK] = setInterval(() => startPromise(monitor()), TASK_POLLING_MS);
    }
  };

  const startBalanceRefresh = (): void => {
    const period = get(refreshPeriod) * MINUTES_TO_MS;
    if (!monitors[MonitorKey.BALANCES] && period > 0) {
      monitors[MonitorKey.BALANCES] = setInterval(() => {
        if (get(canRequestData))
          startPromise(autoRefresh());
      }, period);
    }
  };

  const startEvmStatusMonitoring = (): void => {
    if (!monitors[MonitorKey.EVM_EVENTS_STATUS]) {
      if (get(canRequestData))
        startPromise(fetchTransactionStatusSummary());

      monitors[MonitorKey.EVM_EVENTS_STATUS] = setInterval(() => {
        if (get(canRequestData))
          startPromise(fetchTransactionStatusSummary());
      }, EVM_STATUS_POLLING_MS);
    }
  };

  const startPasswordConfirmationMonitoring = (): void => {
    if (!monitors[MonitorKey.PASSWORD_CONFIRMATION]) {
      monitors[MonitorKey.PASSWORD_CONFIRMATION] = setInterval(() => {
        if (!get(logged))
          return;

        const currentUsername = get(username);
        if (!currentUsername)
          return;

        startPromise(checkIfPasswordConfirmationNeeded(currentUsername));
      }, PASSWORD_CHECK_MS);
    }
  };

  /**
   * This function is called periodically, queries some data from the
   * client and updates the UI with the response.
   */
  const start = function (restarting = false): void {
    startPromise(connectWebSocket(restarting));
    startTaskMonitoring(restarting);
    startBalanceRefresh();
    startEvmStatusMonitoring();
    startPasswordConfirmationMonitoring();
  };

  const stop = (): void => {
    disconnect();
    for (const key in monitors) {
      clearInterval(monitors[key]);
      delete monitors[key];
    }
  };

  const restart = (): void => {
    stop();
    start(true);
  };

  return {
    restart,
    start,
    startTaskMonitoring,
    stop,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMonitorStore, import.meta.hot));
