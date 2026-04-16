import type { SessionConfigPayload } from '@/modules/core/sigil/types';
import { Theme } from '@rotki/common';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

export function useSessionConfigHandler(): () => SessionConfigPayload {
  const { currentTier, premium } = usePremiumHelper();
  const { appVersion } = storeToRefs(useMainStore());
  const { currency, currentPriceOracles } = storeToRefs(useGeneralSettingsStore());
  const { language, selectedTheme } = storeToRefs(useFrontendSettingsStore());
  const { isPackaged } = useInterop();

  return () => ({
    premium: get(premium),
    plan: get(currentTier),
    appVersion: get(appVersion),
    mainCurrency: get(currency).tickerSymbol,
    language: get(language),
    theme: (Theme[get(selectedTheme)] ?? 'AUTO').toLowerCase(),
    appMode: isPackaged ? 'electron' : 'web',
    priceOracles: get(currentPriceOracles).join(','),
  });
}
