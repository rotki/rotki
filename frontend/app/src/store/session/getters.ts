import { GetterTree } from 'vuex';
import { Currency } from '@/model/currency';
import {
  SupportedModules,
  Watcher,
  WatcherType
} from '@/services/session/types';
import { SessionState } from '@/store/session/types';
import { RotkehlchenState } from '@/store/types';
import { Tag } from '@/typing/types';

interface SessionGetters {
  floatingPrecision: number;
  dateDisplayFormat: string;
  lastBalanceSave: number;
  currency: Currency;
  tags: Tag[];
  krakenAccountType: string;
  loanWatchers: Watcher<WatcherType>[];
  activeModules: SupportedModules[];
}

type GettersDefinition = {
  [P in keyof SessionGetters]: (
    state: SessionState,
    getters: SessionGetters
  ) => SessionGetters[P];
};

export const getters: GetterTree<SessionState, RotkehlchenState> &
  GettersDefinition = {
  floatingPrecision: (state: SessionState) => {
    return state.generalSettings.floatingPrecision;
  },

  dateDisplayFormat: (state: SessionState) => {
    return state.generalSettings.dateDisplayFormat;
  },

  thousandSeparator: (state: SessionState) => {
    return state.generalSettings.thousandSeparator;
  },

  decimalSeparator: (state: SessionState) => {
    return state.generalSettings.decimalSeparator;
  },

  currencyLocation: (state: SessionState) => {
    return state.generalSettings.currencyLocation;
  },

  lastBalanceSave: (state: SessionState) => {
    return state.accountingSettings.lastBalanceSave;
  },

  currency: (state: SessionState) => {
    return state.generalSettings.selectedCurrency;
  },

  tags: (state: SessionState) => {
    return Object.values(state.tags);
  },

  krakenAccountType: (state: SessionState) => {
    return state.generalSettings.krakenAccountType;
  },

  loanWatchers: ({ watchers }) => {
    const loanWatcherTypes = ['makervault_collateralization_ratio'];

    return watchers.filter(
      watcher => loanWatcherTypes.indexOf(watcher.type) > -1
    );
  },

  activeModules: ({ generalSettings }) => {
    return generalSettings.activeModules;
  }
};
