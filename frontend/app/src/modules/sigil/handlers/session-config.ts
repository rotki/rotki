import type { SessionConfigPayload } from '@/modules/sigil/types';
import { Theme } from '@rotki/common';
import { useInterop } from '@/composables/electron-interop';
import { useMainStore } from '@/store/main';
import { usePremiumStore } from '@/store/session/premium';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';

export function useSessionConfigHandler(): () => SessionConfigPayload {
  const { premium } = storeToRefs(usePremiumStore());
  const { appVersion } = storeToRefs(useMainStore());
  const { currency, currentPriceOracles } = storeToRefs(useGeneralSettingsStore());
  const { language, selectedTheme } = storeToRefs(useFrontendSettingsStore());
  const { isPackaged } = useInterop();

  return () => ({
    premium: get(premium),
    appVersion: get(appVersion),
    mainCurrency: get(currency).tickerSymbol,
    language: get(language),
    theme: (Theme[get(selectedTheme)] ?? 'AUTO').toLowerCase(),
    appMode: isPackaged ? 'electron' : 'web',
    priceOracles: get(currentPriceOracles).join(','),
  });
}
