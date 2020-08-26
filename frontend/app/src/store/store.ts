import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { VersionCheck } from '@/model/version-check';
import { api } from '@/services/rotkehlchen-api';
import { balances } from '@/store/balances';
import { Section, Status } from '@/store/const';
import { defi } from '@/store/defi';
import { notifications } from '@/store/notifications';
import { reports } from '@/store/reports';
import { session } from '@/store/session';
import { settings } from '@/store/settings';
import { tasks } from '@/store/tasks';
import { trades } from '@/store/trades';
import {
  Message,
  RotkehlchenState,
  StatusPayload,
  Version
} from '@/store/types';

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
    connected: false,
    status: {}
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
    },
    setConnected: (state: RotkehlchenState, connected: boolean) => {
      state.connected = connected;
    },
    setStatus: (state: RotkehlchenState, status: StatusPayload) => {
      state.status = { ...state.status, [status.section]: status.status };
    }
  },
  actions: {
    async version({ commit }): Promise<void> {
      const timerId = setInterval(async function () {
        try {
          const version = await api.checkVersion();
          if (version) {
            commit('versions', version);
            clearInterval(timerId);
          }
          // eslint-disable-next-line no-empty
        } catch (e) {}
      }, 1000);
    },
    async connect({ commit }): Promise<void> {
      const timerId = setInterval(async function () {
        try {
          const connected = await api.ping();
          if (connected) {
            commit('setConnected', connected);
            clearInterval(timerId);
          }
          // eslint-disable-next-line no-empty
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
    },
    status: (state: RotkehlchenState) => (section: Section): Status => {
      return state.status[section] ?? Status.NONE;
    }
  },
  modules: {
    notifications,
    balances,
    defi,
    tasks,
    trades,
    session,
    reports,
    settings
  }
};
export default new Vuex.Store(store);
