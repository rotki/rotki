import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { websocket } from '@/services/websocket/websocket-service';
import { useBalancesStore } from '@/store/balances';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useNotifications } from '@/store/notifications';
import { useSessionStore } from '@/store/session';
import { useWatchersStore } from '@/store/session/watchers';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTasks } from '@/store/tasks';

const PERIODIC = 'periodic';
const TASK = 'task';
const WATCHER = 'watcher';
const BALANCES = 'balances';

class Monitoring {
  private monitors: { [monitor: string]: any } = {};

  private static fetch() {
    useSessionStore().periodicCheck().then();
    const { consume } = useNotifications();
    if (!websocket.connected) {
      consume();
    }
  }

  private static fetchWatchers() {
    useWatchersStore().fetchWatchers().then();
  }

  private static async fetchBalances() {
    const { fetchBlockchainBalances, fetchLoopringBalances } =
      useBlockchainBalancesStore();
    const { refreshPrices } = useBalancesStore();

    const { fetchManualBalances } = useManualBalancesStore();
    const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();

    await fetchManualBalances();
    await fetchBlockchainBalances({ ignoreCache: true });
    await fetchLoopringBalances(true);
    await fetchConnectedExchangeBalances();
    await refreshPrices({ ignoreCache: true });
  }

  /**
   * This function is called periodically, queries some data from the
   * client and updates the UI with the response.
   */
  start(restarting: boolean = false) {
    const { queryPeriod, refreshPeriod } = storeToRefs(
      useFrontendSettingsStore()
    );

    websocket.connect().then(() => {
      if (!this.monitors[PERIODIC]) {
        if (!restarting) {
          Monitoring.fetch();
        }

        this.monitors[PERIODIC] = setInterval(
          Monitoring.fetch,
          get(queryPeriod) * 1000
        );
      }
    });

    if (!this.monitors[TASK]) {
      const { monitor } = useTasks();
      if (!restarting) {
        monitor();
      }
      this.monitors[TASK] = setInterval(() => monitor(), 2000);
    }

    if (!this.monitors[WATCHER]) {
      if (!restarting) {
        Monitoring.fetchWatchers();
      }
      // check for watchers every 6 minutes (approx. half the firing time
      // of the server-side watchers)
      this.monitors[WATCHER] = setInterval(Monitoring.fetchWatchers, 360000);
    }

    const period = get(refreshPeriod) * 60 * 1000;
    if (!this.monitors[BALANCES] && period > 0) {
      this.monitors[BALANCES] = setInterval(Monitoring.fetchBalances, period);
    }
  }

  stop() {
    websocket.disconnect();
    for (const key in this.monitors) {
      clearInterval(this.monitors[key]);
      delete this.monitors[key];
    }
  }

  restart() {
    this.stop();
    this.start(true);
  }
}

export const monitor = new Monitoring();
