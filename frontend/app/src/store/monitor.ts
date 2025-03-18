import { useBalances } from '@/composables/balances';
import { useMessageHandling } from '@/composables/message-handling';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePeriodicStore } from '@/store/session/periodic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { useWebsocketStore } from '@/store/websocket';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { logger } from '@/utils/logging';
import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';

const PERIODIC = 'periodic';
const TASK = 'task';
const BALANCES = 'balances';

export const useMonitorStore = defineStore('monitor', () => {
  const monitors = ref<Record<string, any>>({});

  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { check } = usePeriodicStore();
  const { consume } = useMessageHandling();
  const { monitor } = useTaskStore();
  const { autoRefresh } = useBalances();
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
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
