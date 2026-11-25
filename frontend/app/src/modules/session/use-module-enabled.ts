import { get } from '@vueuse/shared';
import { computed, type MaybeRefOrGetter, type Ref, toValue } from 'vue';
import { Module } from '@/modules/core/common/modules';
import { useSetting } from '@/modules/settings/use-setting';

export { Module };

interface UseModuleEnabledReturn {
  enabled: Readonly<Ref<boolean>>;
}

export function getModuleEnabled(module: Module): boolean {
  const activeModules = useSetting('activeModules');
  return get(activeModules).includes(module);
}

export function useModuleEnabled(module: MaybeRefOrGetter<Module>): UseModuleEnabledReturn {
  const activeModules = useSetting('activeModules');

  const enabled = computed<boolean>(() => get(activeModules).includes(toValue(module)));

  return { enabled };
}
