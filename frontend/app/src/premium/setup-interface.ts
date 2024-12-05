import dayjs from 'dayjs';
import { displayDateFormatter } from '@/data/date-formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import {
  assetsApi,
  balancesApi,
  compoundApi,
  statisticsApi,
  sushiApi,
  userSettings,
  utilsApi,
} from '@/premium/premium-apis';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGraph } from '@/composables/graphs';
import type { DataUtilities, DateUtilities, PremiumInterface, SettingsApi, Themes, TimeUnit } from '@rotki/common';
import type { DateFormat } from '@/types/date-format';
import type { FrontendSettingsPayload } from '@/types/settings/frontend-settings';

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
    compound: compoundApi(),
    statistics: statisticsApi(),
    sushi: sushiApi(),
    utils: utilsApi(),
  };
}

function settings(): SettingsApi {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n();
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
  return {
    api: () => ({
      data: data(),
      date,
      graphs: useGraph,
      settings: settings(),
    }),
    useHostComponents: true,
    version: 25,
  };
}
