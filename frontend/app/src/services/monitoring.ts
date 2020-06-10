import { taskManager } from '@/services/task-manager';
import store from '@/store/store';

class Monitoring {
  private monitoring?: NodeJS.Timer;
  private taskMonitoring?: NodeJS.Timer;
  private watcherMonitoring?: NodeJS.Timer;

  private fetch() {
    store.dispatch('notifications/consume');
    store.dispatch('session/periodicCheck');
  }

  private fetchWatchers() {
    store.dispatch('balances/fetchWatchers');
  }

  /**
   * This function is called periodically, queries some data from the
   * client and updates the UI with the response.
   */
  start() {
    if (!this.monitoring) {
      this.fetch();
      this.monitoring = setInterval(this.fetch, 5000);
    }

    if (!this.taskMonitoring) {
      taskManager.monitor();
      this.taskMonitoring = setInterval(() => taskManager.monitor(), 2000);
    }

    if (!this.watcherMonitoring) {
      this.fetchWatchers();
      this.watcherMonitoring = setInterval(this.fetchWatchers, 60000);
    }
  }

  stop() {
    if (this.monitoring) {
      clearInterval(this.monitoring);
      this.monitoring = undefined;
    }
    if (this.taskMonitoring) {
      clearInterval(this.taskMonitoring);
      this.taskMonitoring = undefined;
    }
  }
}

export const monitor = new Monitoring();
