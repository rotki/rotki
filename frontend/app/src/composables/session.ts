import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';

export const useModules = () => {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isAnyModuleEnabled = (modules: Module[]) => {
    return computed(
      () =>
        get(activeModules).filter(module => modules.includes(module)).length > 0
    );
  };

  const isModuleEnabled = (module: Module) => {
    return computed(() => {
      const active = get(activeModules);
      return active.includes(module);
    });
  };

  return {
    isAnyModuleEnabled,
    isModuleEnabled,
    activeModules
  };
};

export const getPremium = () => {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
};

export const setPremium = (isPremium: boolean) => {
  const { premium } = storeToRefs(usePremiumStore());
  set(premium, isPremium);
};

export const useDarkMode = () => {
  const store = useSessionStore();
  const { darkModeEnabled } = storeToRefs(store);

  const updateDarkMode = (enabled: boolean) => {
    set(darkModeEnabled, enabled);
  };

  return {
    darkModeEnabled,
    updateDarkMode
  };
};
