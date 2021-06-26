import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { BackendVersion } from '@/services/types-api';
import { assets } from '@/store/assets';
import { balances } from '@/store/balances';
import { defiSections, Section, Status } from '@/store/const';
import { storePlugins } from '@/store/debug';
import { defi } from '@/store/defi';
import { history } from '@/store/history';
import { notifications } from '@/store/notifications';
import { reports } from '@/store/reports';
import { session } from '@/store/session';
import { settings } from '@/store/settings';
import { staking } from '@/store/staking';
import { statistics } from '@/store/statistics';
import { tasks } from '@/store/tasks';
import {
  Message,
  RotkehlchenState,
  StatusPayload,
  Version
} from '@/store/types';
import { isLoading } from '@/store/utils';
import { Nullable } from '@/types';

Vue.use(Vuex);

let intervalId: any = null;

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

const defaultState = () => ({
  message: emptyMessage(),
  version: defaultVersion(),
  connected: false,
  connectionFailure: false,
  status: {},
  dataDirectory: ''
});

const store: StoreOptions<RotkehlchenState> = {
  state: defaultState(),
  mutations: {
    setMessage: (state: RotkehlchenState, message: Message) => {
      state.message = message;
    },
    resetMessage: (state: RotkehlchenState) => {
      state.message = emptyMessage();
    },
    versions: (state: RotkehlchenState, version: BackendVersion) => {
      state.version = {
        version: version.ourVersion || '',
        latestVersion: version.latestVersion || '',
        downloadUrl: version.downloadUrl || ''
      };
    },
    dataDirectory(state: RotkehlchenState, directory: string) {
      state.dataDirectory = directory;
    },
    setConnected: (state: RotkehlchenState, connected: boolean) => {
      state.connected = connected;
    },
    setStatus: (state: RotkehlchenState, status: StatusPayload) => {
      state.status = { ...state.status, [status.section]: status.status };
    },
    connectionFailure: (
      state: RotkehlchenState,
      connectionFailure: boolean
    ) => {
      state.connectionFailure = connectionFailure;
    },
    reset: (state: RotkehlchenState) => {
      Object.assign(state, defaultState(), {
        version: state.version,
        connected: state.connected
      });
    }
  },
  actions: {
    async version({ commit }): Promise<void> {
      const { version, dataDirectory } = await api.info();
      if (version) {
        commit('versions', version);
        commit('dataDirectory', dataDirectory);
      }
    },
    async connect({ commit, dispatch }, payload: string | null): Promise<void> {
      let count = 0;
      if (intervalId) {
        clearInterval(intervalId);
      }

      function updateApi(payload?: Nullable<string>) {
        const interopServerUrl = window.interop?.serverUrl();
        let backend = process.env.VUE_APP_BACKEND_URL!;
        if (payload) {
          backend = payload;
        } else if (interopServerUrl) {
          backend = interopServerUrl;
        }
        api.setup(backend);
      }

      const attemptConnect = async function () {
        try {
          updateApi(payload);

          const connected = await api.ping();
          if (connected) {
            clearInterval(intervalId);
            commit('setConnected', connected);
            await dispatch('version');
          }
          // eslint-disable-next-line no-empty
        } catch (e) {
        } finally {
          count++;
          if (count > 20) {
            clearInterval(intervalId);
            commit('connectionFailure', true);
          }
        }
      };
      intervalId = setInterval(attemptConnect, 2000);
      commit('connectionFailure', false);
    },
    async resetDefiStatus({ commit }): Promise<void> {
      const status = Status.NONE;
      defiSections.forEach(section => {
        commit('setStatus', {
          status,
          section
        });
      });
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
    },
    detailsLoading: (state: RotkehlchenState) => {
      return (
        isLoading(state.status[Section.BLOCKCHAIN_ETH]) ||
        isLoading(state.status[Section.BLOCKCHAIN_BTC]) ||
        isLoading(state.status[Section.BLOCKCHAIN_KSM]) ||
        isLoading(state.status[Section.EXCHANGES]) ||
        isLoading(state.status[Section.MANUAL_BALANCES])
      );
    }
  },
  modules: {
    notifications,
    balances,
    defi,
    tasks,
    history,
    session,
    reports,
    settings,
    statistics,
    staking,
    assets
  },
  plugins: storePlugins()
};
export default new Vuex.Store(store);
