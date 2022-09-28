import {
  DataUtilities,
  DateUtilities,
  PremiumInterface,
  SettingsApi
} from '@rotki/common/lib/premium';
import { Themes, TimeUnit } from '@rotki/common/lib/settings';
import dayjs from 'dayjs';
import { displayDateFormatter } from '@/data/date_formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  adexApi,
  assetsApi,
  balancerApi,
  balancesApi,
  compoundApi,
  statisticsApi,
  sushiApi,
  userSettings,
  utilsApi
} from '@/premium/premium-apis';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
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
    return dayjs().subtract(amount, unit).unix();
  },
  toUserSelectedFormat(timestamp: number): string {
    return displayDateFormatter.format(
      new Date(timestamp * 1000),
      useGeneralSettingsStore().dateDisplayFormat
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
  sushi: sushiApi(),
  utils: utilsApi()
});

const settings = (): SettingsApi => {
  const frontendStore = useFrontendSettingsStore();
  const { t, tc } = useI18n();
  return {
    async update(settings: FrontendSettingsPayload): Promise<void> {
      await frontendStore.updateSetting(settings);
    },
    defaultThemes(): Themes {
      return {
        dark: DARK_COLORS,
        light: LIGHT_COLORS
      };
    },
    themes(): Themes {
      return {
        light: frontendStore.lightTheme,
        dark: frontendStore.darkTheme
      };
    },
    user: userSettings(),
    i18n: {
      t,
      tc
    }
  };
};

export const usePremiumApi = (): PremiumInterface => ({
  useHostComponents: true,
  version: 19,
  api: () => ({
    date,
    data: data(),
    settings: settings()
  })
});
