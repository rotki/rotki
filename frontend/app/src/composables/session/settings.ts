import { BigNumber, TimeFramePersist } from '@rotki/common';
import { getBnFormat } from '@/data/amount-formatter';
import type { Exchange } from '@/types/exchanges';
import type { UserSettingsModel } from '@/types/user';

export function useSessionSettings() {
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { update: updateFrontendSettings, checkDefaultThemeVersion } = useFrontendSettingsStore();
  const { update: updateAccountingSettings } = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { update: updateSessionSettings, setConnectedExchanges } = useSessionSettingsStore();

  const initialize = (
    { accounting, general, other: { frontendSettings, havePremium, premiumShouldSync } }: UserSettingsModel,
    exchanges: Exchange[],
  ): void => {
    if (frontendSettings) {
      const { timeframeSetting, lastKnownTimeframe } = frontendSettings;
      const { thousandSeparator, decimalSeparator } = frontendSettings;
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
