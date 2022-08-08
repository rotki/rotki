import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { computed, reactive, toRefs } from '@vue/composition-api';
import {
  createSharedComposable,
  get,
  set,
  useLocalStorage
} from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
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

  const update = async (
    sessionSettings: Partial<SessionSettings>
  ): Promise<ActionStatus> => {
    Object.assign(settings, sessionSettings);
    return {
      success: true
    };
  };

  const reset = () => {
    Object.assign(settings, defaultSessionSettings());
  };

  return {
    ...toRefs(settings),
    shouldShowAmount,
    shouldShowPercentage,
    setAnimationsEnabled,
    update,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useSessionSettingsStore, import.meta.hot)
  );
}
