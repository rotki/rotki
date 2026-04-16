import type { Exchange } from '@/modules/balances/types/exchanges';
import type { UserSettingsModel } from '@/modules/settings/types/user-settings';
import { BigNumber, TimeFramePersist } from '@rotki/common';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { usePremiumWatchers } from '@/modules/premium/use-premium-watchers';
import { PrivacyMode } from '@/modules/session/types';
import { useSettingsSuggestions } from '@/modules/settings/suggestions/use-settings-suggestions';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useThemeMigration } from '@/modules/settings/use-theme-migration';

interface UseSessionSettingsReturn {
  initialize: (model: UserSettingsModel, exchanges: Exchange[]) => Promise<void>;
}

export function useSessionSettings(): UseSessionSettingsReturn {
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { fetchCapabilities } = usePremiumWatchers();
  const { update: updateFrontendSettings } = useFrontendSettingsStore();
  const { updateFrontendSetting } = useSettingsOperations();
  const { update: updateAccountingSettings } = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { setConnectedExchanges, update: updateSessionSettings } = useSessionSettingsStore();
  const { checkDefaultThemeVersion } = useThemeMigration();
  const { checkForSuggestions } = useSettingsSuggestions();

  const initialize = async (
    {
      accounting,
      general,
      other: { frontendSettings, havePremium, premiumShouldSync },
    }: UserSettingsModel,
    exchanges: Exchange[],
  ): Promise<void> => {
    if (frontendSettings) {
      const { lastKnownTimeframe, persistPrivacySettings, timeframeSetting } = frontendSettings;
      const { decimalSeparator, thousandSeparator } = frontendSettings;
      const timeframe = timeframeSetting !== TimeFramePersist.REMEMBER
        ? timeframeSetting
        : lastKnownTimeframe;

      updateFrontendSettings(frontendSettings);
      setConnectedExchanges(exchanges);
      updateSessionSettings({ timeframe });
      BigNumber.config({
        FORMAT: getBnFormat(thousandSeparator, decimalSeparator),
      });
      checkDefaultThemeVersion();
      checkForSuggestions(frontendSettings, general);

      if (!persistPrivacySettings) {
        await updateFrontendSetting({
          privacyMode: PrivacyMode.NORMAL,
          scrambleData: false,
        });
      }
    }

    set(premium, havePremium);
    set(premiumSync, premiumShouldSync);
    updateGeneralSettings(general);
    updateAccountingSettings(accounting);
    await fetchCapabilities();
  };

  return {
    initialize,
  };
}
