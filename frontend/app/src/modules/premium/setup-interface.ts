import type {
  DateUtilities,
  NewGraphApi,
  PremiumApi,
  SettingsApi,
  Themes,
  TimeUnit,
} from '@rotki/common';
import type { DateFormat } from '@/modules/core/common/date-format';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import dayjs from 'dayjs';
import { convertToTimestamp } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import { assetsApi, balancesApi, statisticsApi, userSettings, utilsApi } from '@/modules/premium/premium-apis';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useGraph } from '@/modules/statistics/use-graph';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';

/**
 * Creates the PremiumApi instance.
 * This function must be called from within a Vue component context
 * because it uses Vue composables (useI18n, useFrontendSettingsStore, etc.)
 */
export function createPremiumApi(): PremiumApi {
  const date: DateUtilities = {
    convertToTimestamp(date: string, dateFormat?: string): number {
      return convertToTimestamp(date, dateFormat as DateFormat | undefined);
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
  };

  function createSettings(): SettingsApi {
    // eslint-disable-next-line @typescript-eslint/unbound-method
    const { t, te } = useI18n({ useScope: 'global' });
    const frontendStore = useFrontendSettingsStore();
    const { updateFrontendSetting } = useSettingsOperations();
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
        await updateFrontendSetting(settings);
      },
      user: userSettings(),
    };
  }

  return {
    data: {
      assets: assetsApi(),
      balances: balancesApi(),
      statistics: statisticsApi(),
      utils: utilsApi(),
    },
    date,
    graphs(): NewGraphApi {
      return useGraph();
    },
    logger,
    settings: createSettings(),
  };
}
