import {
  type DataUtilities,
  type DateUtilities,
  type PremiumInterface,
  type SettingsApi
} from '@rotki/common/lib/premium';
import { type Themes, type TimeUnit } from '@rotki/common/lib/settings';
import dayjs from 'dayjs';
import { displayDateFormatter } from '@/data/date_formatter';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  assetsApi,
  balancerApi,
  balancesApi,
  compoundApi,
  statisticsApi,
  sushiApi,
  userSettings,
  utilsApi
} from '@/premium/premium-apis';
import { type DateFormat } from '@/types/date-format';
import { type FrontendSettingsPayload } from '@/types/frontend-settings';

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
  balances: balancesApi(),
  balancer: balancerApi(),
  compound: compoundApi(),
  sushi: sushiApi(),
  utils: utilsApi()
});

const settings = (): SettingsApi => {
  const { t } = useI18n();
  const frontendStore = useFrontendSettingsStore();

  const visibilityStore = useAreaVisibilityStore();
  const { small } = storeToRefs(visibilityStore);

  return {
    async update(settings: FrontendSettingsPayload): Promise<void> {
      await frontendStore.updateSetting(settings);
    },
    display: {
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
      small
    },
    user: userSettings(),
    i18n: {
      t,
      // TODO: deprecate on the next major components version (it's only here for backwards compat)
      tc: (key, choice, values) => {
        if (!isDefined(choice)) {
          return t(key);
        }
        if (!values) {
          return t(key, choice);
        }
        return t(key, values, choice);
      }
    }
  };
};

export const usePremiumApi = (): PremiumInterface => ({
  useHostComponents: true,
  version: 22,
  api: () => ({
    date,
    data: data(),
    settings: settings()
  })
});
