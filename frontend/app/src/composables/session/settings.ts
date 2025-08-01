import type { Exchange } from '@/types/exchanges';
import type { UserSettingsModel } from '@/types/user';
import { BigNumber, TimeFramePersist } from '@rotki/common';
import { useThemeMigration } from '@/composables/settings/theme';
import { getBnFormat } from '@/data/amount-formatter';
import { usePremiumStore } from '@/store/session/premium';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { PrivacyMode } from '@/types/session';

interface UseSessionSettingsReturn {
  initialize: (model: UserSettingsModel, exchanges: Exchange[]) => Promise<void>;
}

export function useSessionSettings(): UseSessionSettingsReturn {
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { update: updateFrontendSettings, updateSetting } = useFrontendSettingsStore();
  const { update: updateAccountingSettings } = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { setConnectedExchanges, update: updateSessionSettings } = useSessionSettingsStore();
  const { checkDefaultThemeVersion } = useThemeMigration();

  const initialize = async (
    { accounting, general, other: { frontendSettings, havePremium, premiumShouldSync } }: UserSettingsModel,
    exchanges: Exchange[],
  ): Promise<void> => {
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

      if (!frontendSettings.persistPrivacySettings) {
        await updateSetting({
          privacyMode: PrivacyMode.NORMAL,
          scrambleData: false,
        });
      }
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
