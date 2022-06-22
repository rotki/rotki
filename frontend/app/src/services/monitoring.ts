import { setupExchanges, setupGeneralBalances } from '@/composables/balances';
import { websocket } from '@/services/websocket/websocket-service';
import { useNotifications } from '@/store/notifications';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { QUERY_PERIOD, REFRESH_PERIOD } from '@/types/frontend-settings';

const PERIODIC = 'periodic';
const TASK = 'task';
const WATCHER = 'watcher';
const BALANCES = 'balances';

class Monitoring {
  private monitors: { [monitor: string]: any } = {};

  private static fetch() {
    store.dispatch('session/periodicCheck');
    const { consume } = useNotifications();
    if (!websocket.connected) {
      consume();
    }
  }

  private static fetchWatchers() {
    store.dispatch('session/fetchWatchers');
  }

  private static async fetchBalances() {
    const {
      fetchManualBalances,
      fetchBlockchainBalances,
      fetchLoopringBalances,
      refreshPrices
    } = setupGeneralBalances();
    const { fetchConnectedExchangeBalances } = setupExchanges();

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
    const settings = store.state.settings!;

    websocket.connect().then(() => {
      if (!this.monitors[PERIODIC]) {
        if (!restarting) {
          Monitoring.fetch();
        }

        this.monitors[PERIODIC] = setInterval(
          Monitoring.fetch,
          settings[QUERY_PERIOD] * 1000
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

    const period = settings[REFRESH_PERIOD] * 60 * 1000;
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
