import { BigNumber, TimeFramePersist } from '@rotki/common';
import { getBnFormat } from '@/data/amount-formatter';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { usePremiumStore } from '@/store/session/premium';
import type { Exchange } from '@/types/exchanges';
import type { UserSettingsModel } from '@/types/user';

interface UseSessionSettingsReturn {
  initialize: (model: UserSettingsModel, exchanges: Exchange[]) => void;
}

export function useSessionSettings(): UseSessionSettingsReturn {
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { update: updateFrontendSettings } = useFrontendSettingsStore();
  const { update: updateAccountingSettings } = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { setConnectedExchanges, update: updateSessionSettings } = useSessionSettingsStore();
  const { checkDefaultThemeVersion } = useThemeMigration();

  const initialize = (
    { accounting, general, other: { frontendSettings, havePremium, premiumShouldSync } }: UserSettingsModel,
    exchanges: Exchange[],
  ): void => {
    if (frontendSettings) {
      const { lastKnownTimeframe, timeframeSetting } = frontendSettings;
      const { decimalSeparator, thousandSeparator } = frontendSettings;
      const timeframe = timeframeSetting !== TimeFramePersist.REMEMBER ? timeframeSetting : lastKnownTimeframe;

      updateFrontendSettings(frontendSettings);
      setConnectedExchanges(exchanges);
      updateSessionSettings({ timeframe });
      BigNumber.config({
        FORMAT: getBnFormat(thousandSeparator, decimalSeparator),
      });
      checkDefaultThemeVersion();
    }

    set(premium, havePremium);
    set(premiumSync, premiumShouldSync);
    updateGeneralSettings(general);
    updateAccountingSettings(accounting);
  };

  return {
    initialize,
  };
}

/**
 * Keeps track of a shared, global instance of the items per page setting.
 *
 * It is shared between the main.ts and settings store, because referencing the store
 * directly, creates issues with tracking.
 */
export const useItemsPerPage = createSharedComposable(() => ref<number>(10));
