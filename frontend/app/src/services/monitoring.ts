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
    store.dispatch('session/fetchWatchers');
  }

  /**
   * This function is called periodically, queries some data from the
   * client and updates the UI with the response.
   */
  start(periodicClientQueryPeriod: number) {
    if (!this.monitoring) {
      this.fetch();
      this.monitoring = setInterval(
        this.fetch,
        periodicClientQueryPeriod * 1000
      );
    }

    if (!this.taskMonitoring) {
      taskManager.monitor();
      this.taskMonitoring = setInterval(() => taskManager.monitor(), 2000);
    }

    if (!this.watcherMonitoring) {
      this.fetchWatchers();
      // check for watchers every 6 minutes (approx. half the firing time
      // of the server-side watchers)
      this.watcherMonitoring = setInterval(this.fetchWatchers, 360000);
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
    if (this.watcherMonitoring) {
      clearInterval(this.watcherMonitoring);
      this.watcherMonitoring = undefined;
    }
  }
}

export const monitor = new Monitoring();
