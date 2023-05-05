import { type Module } from '@/types/modules';

export const useModules = () => {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isAnyModuleEnabled = (modules: Module[]) =>
    computed(() => get(activeModules).some(module => modules.includes(module)));

  const isModuleEnabled = (module: Module) =>
    computed(() => {
      const active = get(activeModules);
      return active.includes(module);
    });

  return {
    isAnyModuleEnabled,
    isModuleEnabled,
    activeModules
  };
};
