import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { PrivacyMode } from '@/store/session/types';
import { ActionStatus } from '@/store/types';

const useSharedLocalStorage = createSharedComposable(useLocalStorage);
const isAnimationEnabledSetting = useSharedLocalStorage(
  'rotki.animations_enabled',
  true
);

export interface SessionSettings {
  privacyMode: PrivacyMode;
  scrambleData: boolean;
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

const defaultSessionSettings = (): SessionSettings => ({
  privacyMode: PrivacyMode.NORMAL,
  scrambleData: false,
  timeframe: TimeFramePeriod.ALL,
  animationsEnabled: get(isAnimationEnabledSetting)
});

export const useSessionSettingsStore = defineStore('settings/session', () => {
  const settings = reactive(defaultSessionSettings());

  const privacyMode = computed(() => settings.privacyMode);
  const scrambleData = computed(() => settings.scrambleData);
  const timeframe = computed(() => settings.timeframe);
  const animationsEnabled = computed(() => settings.animationsEnabled);

  const shouldShowAmount = computed(() => {
    return settings.privacyMode < PrivacyMode.SEMI_PRIVATE;
  });

  const shouldShowPercentage = computed(() => {
    return settings.privacyMode < PrivacyMode.PRIVATE;
  });

  const setAnimationsEnabled = (enabled: boolean) => {
    set(isAnimationEnabledSetting, enabled);
    settings.animationsEnabled = enabled;
  };

  const update = (sessionSettings: Partial<SessionSettings>): ActionStatus => {
    Object.assign(settings, sessionSettings);
    return {
      success: true
    };
  };

  return {
    privacyMode,
    scrambleData,
    timeframe,
    animationsEnabled,
    shouldShowAmount,
    shouldShowPercentage,
    setAnimationsEnabled,
    update
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useSessionSettingsStore, import.meta.hot)
  );
}
