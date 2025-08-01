import type { ActionStatus } from '@/types/action';
import type { Exchange } from '@/types/exchanges';
import type { SessionSettings } from '@/types/session';
import { TimeFramePeriod } from '@rotki/common';
import { useComputedRef } from '@/composables/utils/useComputedRef';

const useSharedLocalStorage = createSharedComposable(useLocalStorage);
const isAnimationEnabledSetting = useSharedLocalStorage('rotki.animations_enabled', true);

function defaultSessionSettings(): SessionSettings {
  return {
    animationsEnabled: get(isAnimationEnabledSetting),
    timeframe: TimeFramePeriod.ALL,
  };
}

export const useSessionSettingsStore = defineStore('settings/session', () => {
  const settings = ref(defaultSessionSettings());
  const connectedExchanges = ref<Exchange[]>([]);

  const timeframe = useComputedRef(settings, 'timeframe');
  const animationsEnabled = useComputedRef(settings, 'animationsEnabled');

  const setConnectedExchanges = (exchanges: Exchange[]): void => {
    set(connectedExchanges, exchanges);
  };

  const setAnimationsEnabled = (enabled: boolean): void => {
    set(isAnimationEnabledSetting, enabled);
    set(settings, {
      ...get(settings),
      animationsEnabled: enabled,
    });
  };

  const update = (sessionSettings: Partial<SessionSettings>): ActionStatus => {
    set(settings, {
      ...get(settings),
      ...sessionSettings,
    });
    return {
      success: true,
    };
  };

  return {
    animationsEnabled,
    connectedExchanges,
    setAnimationsEnabled,
    setConnectedExchanges,
    settings,
    timeframe,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionSettingsStore, import.meta.hot));
