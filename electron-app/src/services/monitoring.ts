import { service } from '@/services/rotkehlchen_service';
import store from '@/store';

class Monitoring {
  private monitoring?: NodeJS.Timer;

  private fetch() {
    service
      .query_periodic_data()
      .then(result => {
        if (Object.keys(result).length === 0) {
          // an empty object means user is not logged in yet
          return;
        }

        store.commit('updateAccountingSetting', {
          lastBalanceSave: result['last_balance_save']
        });

        store.commit('nodeConnection', result['eth_node_connection']);
        store.commit('historyProcess', result['history_process_current_ts']);
      })
      .catch(reason => {
        const error_string = 'Error at periodic client query: ' + reason;
      });
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
  }

  stop() {
    if (!this.monitoring) {
      return;
    }
    clearInterval(this.monitoring);
  }
}

export const monitor = new Monitoring();
