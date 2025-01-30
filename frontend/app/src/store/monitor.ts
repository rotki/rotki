import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { logger } from '@/utils/logging';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useWatchersStore } from '@/store/session/watchers';
import { usePeriodicStore } from '@/store/session/periodic';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useWebsocketStore } from '@/store/websocket';
import { useTaskStore } from '@/store/tasks';
import { useBalances } from '@/composables/balances';
import { useBlockchainBalances } from '@/composables/blockchain/balances';
import { useMessageHandling } from '@/composables/message-handling';

const PERIODIC = 'periodic';
const TASK = 'task';
const WATCHER = 'watcher';
const BALANCES = 'balances';

export const useMonitorStore = defineStore('monitor', () => {
  const monitors = ref<Record<string, any>>({});

  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { check } = usePeriodicStore();
  const { consume } = useMessageHandling();
  const { fetchWatchers } = useWatchersStore();
  const { monitor } = useTaskStore();
  const { autoRefresh } = useBalances();
  const { fetchManualBalances } = useManualBalancesStore();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();

  const frontendStore = useFrontendSettingsStore();
  const { balanceUsdValueThreshold, queryPeriod, refreshPeriod } = storeToRefs(frontendStore);

  const ws = useWebsocketStore();
  const { connected } = storeToRefs(ws);
  const { connect, disconnect } = ws;

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

  const startWatcherMonitoring = (restarting: boolean): void => {
    const activeMonitors = get(monitors);
    if (!activeMonitors[WATCHER]) {
      if (!restarting && get(canRequestData))
        startPromise(fetchWatchers());

      // check for watchers every 6 minutes (approx. half the firing time
      // of the server-side watchers)
      activeMonitors[WATCHER] = setInterval(() => {
        if (!get(canRequestData))
          return;

        startPromise(fetchWatchers());
      }, 360000);
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

  /**
   * This function is called periodically, queries some data from the
   * client and updates the UI with the response.
   */
  const start = function (restarting = false): void {
    startPromise(connectWebSocket(restarting));
    startTaskMonitoring(restarting);
    startWatcherMonitoring(restarting);
    startBalanceRefresh();
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

  watch(balanceUsdValueThreshold, (current, old) => {
    if (!isEqual(current[BalanceSource.MANUAL], old[BalanceSource.MANUAL])) {
      startPromise(fetchManualBalances(true));
    }

    if (!isEqual(current[BalanceSource.EXCHANGES], old[BalanceSource.EXCHANGES])) {
      startPromise(fetchConnectedExchangeBalances(false));
    }

    if (!isEqual(current[BalanceSource.BLOCKCHAIN], old[BalanceSource.BLOCKCHAIN])) {
      startPromise(fetchBlockchainBalances());
    }
  });

  return {
    restart,
    start,
    stop,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMonitorStore, import.meta.hot));
