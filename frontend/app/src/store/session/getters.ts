import { Watcher, WatcherType } from '@/services/session/types';
import { PrivacyMode, SessionState } from '@/store/session/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { Currency } from '@/types/currency';
import { Module } from '@/types/modules';
import { READ_ONLY_TAGS, Tag, Tags } from '@/types/user';

interface SessionGetters {
  floatingPrecision: number;
  dateDisplayFormat: string;
  currency: Currency;
  tags: Tag[];
  availableTags: Tags;
  availableTagsArray: Tag[];
  loanWatchers: Watcher<WatcherType>[];
  activeModules: Module[];
  currencySymbol: string;
  shouldShowAmount: boolean;
  shouldShowPercentage: boolean;
}

export const getters: Getters<
  SessionState,
  SessionGetters,
  RotkehlchenState,
  any
> = {
  floatingPrecision: (state: SessionState) => {
    return state.generalSettings.uiFloatingPrecision;
  },

  dateDisplayFormat: (state: SessionState) => {
    return state.generalSettings.dateDisplayFormat;
  },

  currency: (state: SessionState) => {
    return state.generalSettings.mainCurrency;
  },

  currencySymbol: (_, getters) => {
    return getters.currency.tickerSymbol;
  },

  tags: (state: SessionState) => {
    return Object.values(state.tags);
  },

  availableTags: (state: SessionState) => {
    return { ...state.tags, ...READ_ONLY_TAGS };
  },

  availableTagsArray: (state: SessionState) => {
    return Object.values({ ...state.tags, ...READ_ONLY_TAGS });
  },

  loanWatchers: ({ watchers }) => {
    const loanWatcherTypes = ['makervault_collateralization_ratio'];

    return watchers.filter(
      watcher => loanWatcherTypes.indexOf(watcher.type) > -1
    );
  },

  activeModules: ({ generalSettings }) => {
    return generalSettings.activeModules;
  },

  shouldShowAmount: ({ privacyMode }) => {
    return privacyMode < PrivacyMode.SEMI_PRIVATE;
  },

  shouldShowPercentage: ({ privacyMode }) => {
    return privacyMode < PrivacyMode.PRIVATE;
  }
};
