import { service } from '@/services/rotkehlchen_service';
import store from '@/store/store';
import { taskManager } from '@/services/task_manager';

class Monitoring {
  private monitoring?: NodeJS.Timer;
  private taskMonitoring?: NodeJS.Timer;

  private fetch() {
    store.dispatch('notifications/consume');
    store.dispatch('session/periodicCheck');
  }

  /**
   * This function is called periodically, query some data from the
   * client and update the UI with the response.
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
