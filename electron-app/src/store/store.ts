import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { notifications } from '@/store/notifications';
import { balances } from '@/store/balances';
import { tasks } from '@/store/tasks';
import { session } from '@/store/session';
import { reports } from '@/store/reports';
import { service } from '@/services/rotkehlchen_service';
import { VersionCheck } from '@/model/version-check';

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
    url: ''
  } as Version);

const store: StoreOptions<RotkehlchenState> = {
  state: {
    message: emptyMessage(),
    version: defaultVersion()
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
        url: version.url || ''
      };
    }
  },
  actions: {
    async version({ commit }): Promise<void> {
      try {
        const version = await service.version_check();
        commit('versions', version);
      } catch (e) {
        console.error(e);
      }
    }
  },
  getters: {
    updateNeeded: (state: RotkehlchenState) => {
      const { version, url } = state.version;
      return version.indexOf('dev') >= 0 ? false : !!url;
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
  readonly url: string;
}

export interface RotkehlchenState {
  message: Message;
  version: Version;
}

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}
