import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { PrivacyMode } from '@/store/session/types';
import { type ActionStatus } from '@/store/types';

const useSharedLocalStorage = createSharedComposable(useLocalStorage);
const isAnimationEnabledSetting = useSharedLocalStorage(
  'rotki.animations_enabled',
  true
);

export interface SessionSettings {
  privacyMode: PrivacyMode;
  scrambleData: boolean;
  scrambleMultiplier: number;
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

const generateRandomScrambleMultiplier = () => {
  // Generate random number from 0.5 to 10
  return Math.floor(500 + Math.random() * 9500) / 1000;
};

const defaultSessionSettings = (): SessionSettings => ({
  privacyMode: PrivacyMode.NORMAL,
  scrambleData: false,
  scrambleMultiplier: generateRandomScrambleMultiplier(),
  timeframe: TimeFramePeriod.ALL,
  animationsEnabled: get(isAnimationEnabledSetting)
});

export const useSessionSettingsStore = defineStore('settings/session', () => {
  const settings = reactive(defaultSessionSettings());

  const privacyMode = computed(() => settings.privacyMode);
  const scrambleData = computed(() => settings.scrambleData);
  const scrambleMultiplier = computed(() => settings.scrambleMultiplier);
  const timeframe = computed(() => settings.timeframe);
  const animationsEnabled = computed(() => settings.animationsEnabled);

  const shouldShowAmount = computed(() => {
    return settings.privacyMode < PrivacyMode.SEMI_PRIVATE;
  });

  const shouldShowPercentage = computed(() => {
    return settings.privacyMode < PrivacyMode.PRIVATE;
  });

  const setAnimationsEnabled = (enabled: boolean): void => {
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
    scrambleMultiplier,
    setAnimationsEnabled,
    update
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useSessionSettingsStore, import.meta.hot)
  );
}
