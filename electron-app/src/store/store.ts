import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { notifications } from '@/store/notifications';
import { balances } from '@/store/balances';
import { tasks } from '@/store/tasks';
import { session } from '@/store/session';
import { reports } from '@/store/reports';
import { api } from '@/services/rotkehlchen-api';
import { VersionCheck } from '@/model/version-check';
import { SessionState } from '@/store/session/state';
import { TaskState } from '@/store/tasks/state';
import { NotificationState } from '@/store/notifications/state';
import { TaxReportState } from '@/store/reports/state';
import { BalanceState } from '@/store/balances/state';

Vue.use(Vuex);

const emptyMessage = (): Message => ({
  title: '',
  description: '',
  success: false
});

const defaultVersion = () =>
  ({
    version: '',
    latestVersion: '',
    downloadUrl: ''
  } as Version);

const store: StoreOptions<RotkehlchenState> = {
  state: {
    message: emptyMessage(),
    version: defaultVersion(),
    connected: false
  },
  mutations: {
    setMessage: (state: RotkehlchenState, message: Message) => {
      state.message = message;
    },
    resetMessage: (state: RotkehlchenState) => {
      state.message = emptyMessage();
    },
    versions: (state: RotkehlchenState, version: VersionCheck) => {
      state.version = {
        version: version.our_version || '',
        latestVersion: version.latest_version || '',
        downloadUrl: version.download_url || ''
      };
      state.connected = true;
    }
  },
  actions: {
    async version({ commit }): Promise<void> {
      const timerId = setInterval(async function() {
        try {
          const version = await api.checkVersion();
          if (version) {
            commit('versions', version);
            clearInterval(timerId);
          }
        } catch (e) {}
      }, 1000);
    }
  },
  getters: {
    updateNeeded: (state: RotkehlchenState) => {
      const { version, downloadUrl } = state.version;
      return version.indexOf('dev') >= 0 ? false : !!downloadUrl;
    },
    version: (state: RotkehlchenState) => {
      const { version } = state.version;
      const indexOfDev = version.indexOf('dev');
      return indexOfDev > 0 ? version.substring(0, indexOfDev + 3) : version;
    },
    message: (state: RotkehlchenState) => {
      return state.message.title.length > 0;
    }
  },
  modules: {
    notifications,
    balances,
    tasks,
    session,
    reports
  }
};
export default new Vuex.Store(store);

export interface Version {
  readonly version: string;
  readonly latestVersion: string;
  readonly downloadUrl: string;
}

export interface RotkehlchenState {
  message: Message;
  version: Version;
  connected: boolean;
  session?: SessionState;
  tasks?: TaskState;
  notifications?: NotificationState;
  reports?: TaxReportState;
  balances?: BalanceState;
}

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}
