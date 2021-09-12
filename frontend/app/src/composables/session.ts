import { computed } from '@vue/composition-api';
import { Module } from '@/services/session/consts';
import { useStore } from '@/store/utils';
import { assert } from '@/utils/assertions';

export const setupModuleEnabled = () => {
  const store = useStore();
  const sessionState = store.state.session;
  assert(sessionState);
  return {
    isModuleEnabled: (module: Module) => {
      return computed(() => {
        const { activeModules } = sessionState.generalSettings;
        return activeModules.includes(module);
      });
    }
  };
};
