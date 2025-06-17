import type { DateFormat } from '@/types/date-format';
import type { FrontendSettingsPayload } from '@/types/settings/frontend-settings';
import type {
  DataUtilities,
  DateUtilities,
  GraphApi,
  NewGraphApi,
  PremiumApi,
  PremiumInterface,
  SettingsApi,
  Themes,
  TimeUnit,
} from '@rotki/common';
import { useGraph, useNewGraph } from '@/composables/graphs';
import { displayDateFormatter } from '@/data/date-formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  assetsApi,
  balancesApi,
  statisticsApi,
  userSettings,
  utilsApi,
} from '@/premium/premium-apis';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import dayjs from 'dayjs';

const date: DateUtilities = {
  convertToTimestamp(date: string, dateFormat?: string): number {
    return convertToTimestamp(date, dateFormat as DateFormat | undefined);
  },
  dateToEpoch(date: string, format: string): number {
    return dayjs(date, format).unix();
  },
  epoch(): number {
    return dayjs().unix();
  },
  epochStartSubtract(amount: number, unit: TimeUnit): number {
    return dayjs().subtract(amount, unit).unix();
  },
  epochToFormat(epoch: number, format: string): string {
    return dayjs(epoch * 1000).format(format);
  },
  format(date: string, _: string, newFormat: string): string {
    return dayjs(date).format(newFormat);
  },
  getDateInputISOFormat(format: string): string {
    return getDateInputISOFormat(format as DateFormat);
  },
  now(format: string): string {
    return dayjs().format(format);
  },
  toUserSelectedFormat(timestamp: number): string {
    return displayDateFormatter.format(new Date(timestamp * 1000), useGeneralSettingsStore().dateDisplayFormat);
  },
};

function data(): DataUtilities {
  return {
    assets: assetsApi(),
    balances: balancesApi(),
    statistics: statisticsApi(),
    utils: utilsApi(),
  };
}

function settings(): SettingsApi {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n({ useScope: 'global' });
  const frontendStore = useFrontendSettingsStore();
  return {
    defaultThemes(): Themes {
      return {
        dark: DARK_COLORS,
        light: LIGHT_COLORS,
      };
    },
    i18n: {
      t,
      te,
    },
    isDark: useRotkiTheme().isDark,
    themes(): Themes {
      return {
        dark: frontendStore.darkTheme,
        light: frontendStore.lightTheme,
      };
    },
    async update(settings: FrontendSettingsPayload): Promise<void> {
      await frontendStore.updateSetting(settings);
    },
    user: userSettings(),
  };
}

export function usePremiumApi(): PremiumInterface {
  function graphs(canvasId: string): GraphApi;
  function graphs(): NewGraphApi;

  function graphs(canvasId?: string): GraphApi | NewGraphApi {
    return canvasId ? useGraph(canvasId) : useNewGraph();
  }

  return {
    api: (): PremiumApi => ({
      data: data(),
      date,
      graphs,
      settings: settings(),
    }),
    useHostComponents: true,
    version: 26,
  };
}
