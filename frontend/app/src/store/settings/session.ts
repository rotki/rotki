import { TimeFramePeriod } from '@rotki/common';
import { PrivacyMode, type SessionSettings } from '@/types/session';
import type { ActionStatus } from '@/types/action';
import type { Exchange } from '@/types/exchanges';

const useSharedLocalStorage = createSharedComposable(useLocalStorage);
const isAnimationEnabledSetting = useSharedLocalStorage('rotki.animations_enabled', true);

function defaultSessionSettings(): SessionSettings {
  return {
    privacyMode: PrivacyMode.NORMAL,
    scrambleData: false,
    scrambleMultiplier: generateRandomScrambleMultiplier(),
    timeframe: TimeFramePeriod.ALL,
    animationsEnabled: get(isAnimationEnabledSetting),
  };
}

export const useSessionSettingsStore = defineStore('settings/session', () => {
  const settings = ref(defaultSessionSettings());
  const connectedExchanges = ref<Exchange[]>([]);

  const privacyMode = useComputedRef(settings, 'privacyMode');
  const scrambleData = useComputedRef(settings, 'scrambleData');
  const scrambleMultiplier = useComputedRef(settings, 'scrambleMultiplier');
  const timeframe = useComputedRef(settings, 'timeframe');
  const animationsEnabled = useComputedRef(settings, 'animationsEnabled');
  const shouldShowAmount = computed(() => get(settings).privacyMode < PrivacyMode.SEMI_PRIVATE);
  const shouldShowPercentage = computed(() => get(settings).privacyMode < PrivacyMode.PRIVATE);

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
    privacyMode,
    scrambleData,
    timeframe,
    animationsEnabled,
    shouldShowAmount,
    shouldShowPercentage,
    scrambleMultiplier,
    connectedExchanges,
    settings,
    setAnimationsEnabled,
    setConnectedExchanges,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionSettingsStore, import.meta.hot));
