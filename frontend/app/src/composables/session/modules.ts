import type { ComputedRef } from 'vue';
import type { Module } from '@/types/modules';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UseModulesReturn {
  isAnyModuleEnabled: (modules: Module[]) => ComputedRef<boolean>;
  isModuleEnabled: (module: Module) => ComputedRef<boolean>;
  activeModules: ComputedRef<Module[]>;
}

export function useModules(): UseModulesReturn {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isAnyModuleEnabled = (modules: Module[]): ComputedRef<boolean> =>
    computed(() => get(activeModules).some(module => modules.includes(module)));

  const isModuleEnabled = (module: Module): ComputedRef<boolean> => computed(() => {
    const active = get(activeModules);
    return active.includes(module);
  });

  return {
    activeModules,
    isAnyModuleEnabled,
    isModuleEnabled,
  };
}
