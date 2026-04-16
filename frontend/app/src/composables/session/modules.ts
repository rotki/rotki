import type { MaybeRefOrGetter, Ref } from 'vue';
import { Module } from '@/modules/common/modules';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

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
