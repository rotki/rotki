import {
  DataUtilities,
  DateUtilities,
  PremiumInterface,
  SettingsApi
} from '@rotki/common/lib/premium';
import {
  DARK_THEME,
  LIGHT_THEME,
  Themes,
  TimeUnit
} from '@rotki/common/lib/settings';
import * as CompositionAPI from '@vue/composition-api';
import * as BigNumber from 'bignumber.js';
import Chart from 'chart.js';
import dayjs from 'dayjs';
import Vue from 'vue';
import * as zod from 'zod';
import { displayDateFormatter } from '@/data/date_formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  adexApi,
  assetsApi,
  balancerApi,
  balancesApi,
  compoundApi,
  dexTradeApi,
  statisticsApi,
  sushiApi,
  userSettings,
  utilsApi
} from '@/premium/premium-apis';
import { registerComponents } from '@/premium/register-components';
import store from '@/store/store';
import { DateFormat } from '@/types/date-format';
import { FrontendSettingsPayload } from '@/types/frontend-settings';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

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
  },
  getDateInputISOFormat(format: string): string {
    return getDateInputISOFormat(format as DateFormat);
  },
  convertToTimestamp(date: string, dateFormat: string): number {
    return convertToTimestamp(date, dateFormat as DateFormat);
  }
};

const data = (): DataUtilities => ({
  assets: assetsApi(),
  statistics: statisticsApi(),
  adex: adexApi(),
  balances: balancesApi(),
  balancer: balancerApi(),
  compound: compoundApi(),
  dexTrades: dexTradeApi(),
  sushi: sushiApi(),
  utils: utilsApi()
});

const settings = (): SettingsApi => ({
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
  },
  user: userSettings()
});

export const usePremiumApi = (): PremiumInterface => ({
  useHostComponents: true,
  version: 16,
  api: {
    date,
    data: data(),
    settings: settings()
  }
});

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window['@vue/composition-api'] = CompositionAPI;
  window.zod = zod;
  window.bn = BigNumber;
  registerComponents();
};
