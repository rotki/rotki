import type { MaybeRefOrGetter, Ref } from 'vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';

export { Module };

interface UseModuleEnabledReturn {
  enabled: Readonly<Ref<boolean>>;
}

export function getModuleEnabled(module: Module): boolean {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  return get(activeModules).includes(module);
}

export function useModuleEnabled(module: MaybeRefOrGetter<Module>): UseModuleEnabledReturn {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const enabled = computed<boolean>(() => get(activeModules).includes(toValue(module)));

  return { enabled: readonly(enabled) };
}
