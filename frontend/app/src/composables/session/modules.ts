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
