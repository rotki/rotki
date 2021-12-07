import {
  GitcoinGrantEventsPayload,
  GitcoinReportPayload
} from '@rotki/common/lib/gitcoin';
import {
  DataUtilities,
  DateUtilities,
  SettingsApi
} from '@rotki/common/lib/premium';
import {
  DARK_THEME,
  LIGHT_THEME,
  Themes,
  TimeUnit
} from '@rotki/common/lib/settings';
import * as CompositionAPI from '@vue/composition-api';
import Chart from 'chart.js';
import dayjs from 'dayjs';
import Vue from 'vue';
import Vuex from 'vuex';
import { displayDateFormatter } from '@/data/date_formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { registerComponents } from '@/premium/register-components';
import { statisticsApi } from '@/premium/statistics-api';
import { api } from '@/services/rotkehlchen-api';
import { HistoryActions } from '@/store/history/consts';
import store from '@/store/store';
import { FrontendSettingsPayload } from '@/types/frontend-settings';

const date: DateUtilities = {
  epoch(): number {
    return dayjs().unix();
  },
  format(date: string, _: string, newFormat: string): string {
    return dayjs(date).format(newFormat);
  },
  now(format: string): string {
    return dayjs().format(format);
  },
  epochToFormat(epoch: number, format: string): string {
    return dayjs(epoch * 1000).format(format);
  },
  dateToEpoch(date: string, format: string): number {
    return dayjs(date, format).unix();
  },
  epochStartSubtract(amount: number, unit: TimeUnit): number {
    return dayjs().subtract(amount, unit).startOf(unit).unix();
  },
  toUserSelectedFormat(timestamp: number): string {
    return displayDateFormatter.format(
      new Date(timestamp * 1000),
      store.getters['session/dateDisplayFormat']
    );
  }
};

const data: DataUtilities = {
  assetInfo: (identifier: string) => {
    return store.getters['balances/assetInfo'](identifier);
  },
  getIdentifierForSymbol: (symbol: string) => {
    return store.getters['balances/getIdentifierForSymbol'](symbol);
  },
  gitcoin: {
    generateReport(payload: GitcoinReportPayload) {
      return api.history.generateReport(payload);
    },
    deleteGrant(grantId: number) {
      return api.history.deleteGitcoinGrantEvents(grantId);
    },
    fetchGrantEvents(payload: GitcoinGrantEventsPayload) {
      return store.dispatch(
        `history/${HistoryActions.FETCH_GITCOIN_GRANT}`,
        payload
      );
    }
  },
  statistics: statisticsApi
};

const settings: SettingsApi = {
  async update(settings: FrontendSettingsPayload): Promise<void> {
    await store.dispatch('settings/updateSetting', settings);
  },
  defaultThemes(): Themes {
    return {
      dark: DARK_COLORS,
      light: LIGHT_COLORS
    };
  },
  themes(): Themes {
    const settings = store.state.settings!;
    return {
      light: settings[LIGHT_THEME],
      dark: settings[DARK_THEME]
    };
  }
};

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.Vue.use(Vuex);
  window['@vue/composition-api'] = CompositionAPI;
  window.rotki = {
    useHostComponents: true,
    version: 16,
    utils: {
      date,
      data,
      settings
    }
  };
  registerComponents();
};
