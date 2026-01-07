import { startPromise } from '@shared/utils';
import { useBalances } from '@/composables/balances';
import { useMonitorWatchers } from '@/composables/monitor/use-monitor-watchers';
import { useAutoLogin } from '@/composables/user/account';
import { useMessageHandling } from '@/modules/messaging';
import { useHistoryStore } from '@/store/history';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePeriodicStore } from '@/store/session/periodic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { useWebsocketStore } from '@/store/websocket';
import { logger } from '@/utils/logging';

const PERIODIC = 'periodic';
const TASK = 'task';
const BALANCES = 'balances';
const EVM_EVENTS_STATUS = 'evm_events_status';
const PASSWORD_CONFIRMATION = 'password_confirmation';

export const useMonitorStore = defineStore('monitor', () => {
  const monitors = ref<Record<string, any>>({});

  const authStore = useSessionAuthStore();
  const { canRequestData, logged, username } = storeToRefs(authStore);
  const { checkIfPasswordConfirmationNeeded } = useAutoLogin();
  const { check } = usePeriodicStore();
  const { consume } = useMessageHandling();
  const { monitor } = useTaskStore();
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
      const activeMonitors = get(monitors);
      if (!activeMonitors[PERIODIC]) {
        if (!restarting)
          fetch();

        activeMonitors[PERIODIC] = setInterval(fetch, get(queryPeriod) * 1000);
        set(monitors, activeMonitors);
      }
    }
    catch (error: any) {
      logger.error(error);
    }
  };

  const startTaskMonitoring = (restarting: boolean): void => {
    const activeMonitors = get(monitors);

    if (!activeMonitors[TASK]) {
      if (!restarting)
        startPromise(monitor());

      activeMonitors[TASK] = setInterval(() => startPromise(monitor()), 2000);
      set(monitors, activeMonitors);
    }
  };

  const startBalanceRefresh = (): void => {
    const period = get(refreshPeriod) * 60 * 1000;
    const activeMonitors = get(monitors);
    if (!activeMonitors[BALANCES] && period > 0) {
      activeMonitors[BALANCES] = setInterval(() => {
        if (get(canRequestData))
          startPromise(autoRefresh());
      }, period);
      set(monitors, activeMonitors);
    }
  };

  const startEvmStatusMonitoring = (): void => {
    const activeMonitors = get(monitors);
    const period = 10 * 60 * 1000; // fetch every 10 mins
    if (!activeMonitors[EVM_EVENTS_STATUS]) {
      if (get(canRequestData))
        startPromise(fetchTransactionStatusSummary());

      activeMonitors[EVM_EVENTS_STATUS] = setInterval(() => {
        if (get(canRequestData))
          startPromise(fetchTransactionStatusSummary());
      }, period);
      set(monitors, activeMonitors);
    }
  };

  const startPasswordConfirmationMonitoring = (): void => {
    const activeMonitors = get(monitors);
    const period = 60 * 60 * 1000; // check every 1 hour
    if (!activeMonitors[PASSWORD_CONFIRMATION]) {
      activeMonitors[PASSWORD_CONFIRMATION] = setInterval(() => {
        if (!get(logged))
          return;

        const currentUsername = get(username);
        if (!currentUsername)
          return;

        startPromise(checkIfPasswordConfirmationNeeded(currentUsername));
      }, period);
      set(monitors, activeMonitors);
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
    const activeMonitors = get(monitors);
    for (const key in activeMonitors) {
      clearInterval(activeMonitors[key]);
      delete activeMonitors[key];
    }
    set(monitors, activeMonitors);
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
