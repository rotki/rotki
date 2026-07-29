import type { Exchange } from '@/modules/balances/types/exchanges';
import type { UserSettingsModel } from '@/modules/settings/types/user-settings';
import { TimeFramePersist } from '@rotki/common';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { usePremiumWatchers } from '@/modules/premium/use-premium-watchers';
import { PrivacyMode } from '@/modules/session/types';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useSettingsSuggestions } from '@/modules/settings/suggestions/use-settings-suggestions';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useThemeMigration } from '@/modules/settings/use-theme-migration';

interface UseSessionSettingsReturn {
  initialize: (model: UserSettingsModel, exchanges: Exchange[], newAccount?: boolean) => Promise<void>;
}

export function useSessionSettings(): UseSessionSettingsReturn {
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { fetchCapabilities } = usePremiumWatchers();
  const {
    updateAccounting: updateAccountingSettings,
    updateFrontend: updateFrontendSettings,
    updateGeneral: updateGeneralSettings,
    updateSession: updateSessionSettings,
  } = useSettingsRepo();
  const { updateFrontendSetting } = useSettingsOperations();
  const { setConnectedExchanges } = useConnectedExchangesStore();
  const { checkDefaultThemeVersion } = useThemeMigration();
  const { checkForSuggestions } = useSettingsSuggestions();

  const initialize = async (
    {
      accounting,
      general,
      other: { frontendSettings, havePremium, premiumShouldSync },
    }: UserSettingsModel,
    exchanges: Exchange[],
    newAccount = false,
  ): Promise<void> => {
    if (frontendSettings) {
      const { lastKnownTimeframe, persistPrivacySettings, timeframeSetting } = frontendSettings;
      const timeframe = timeframeSetting !== TimeFramePersist.REMEMBER
        ? timeframeSetting
        : lastKnownTimeframe;

      // Merging the frontend blob into the repo runs the registry's post-persist effects, which
      // includes reconfiguring the global BigNumber format from the separators.
      updateFrontendSettings(frontendSettings);
      setConnectedExchanges(exchanges);
      updateSessionSettings({ timeframe });
      checkDefaultThemeVersion();
      // Awaited before the privacy reset below: both go through the same read-modify-write of
      // the settings blob, so overlapping them can lose the applied-suggestions version.
      await checkForSuggestions(frontendSettings, general, newAccount);

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
