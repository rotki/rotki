import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  UsdToFiatExchangeRates,
  GeneralSettings,
  ExchangeInfo,
  ExchangeData
} from '@/typing/types';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import { assetSum } from '@/utils/calculation';
import { notifications } from '@/store/notifications';
import { balances } from '@/store/balances';
import { tasks } from '@/store/tasks';
import { session } from '@/store/session';

Vue.use(Vuex);

let store: StoreOptions<RotkehlchenState> = {
  state: {
    historyProcess: 0
  },
  mutations: {
    historyProcess(state: RotkehlchenState, historyProcess: number) {
      state.historyProcess = historyProcess;
    }
  },
  actions: {},
  getters: {},
  modules: {
    notifications,
    balances,
    tasks,
    session
  }
};
export default new Vuex.Store(store);

export interface RotkehlchenState {
  historyProcess: number;
}
