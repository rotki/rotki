import { computed } from '@vue/composition-api';
import { Module } from '@/services/session/consts';
import { SessionState } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { assert } from '@/utils/assertions';

function getSessionState(): SessionState {
  const store = useStore();
  const sessionState = store.state.session;
  assert(sessionState);
  return sessionState;
}

export const setupModuleEnabled = () => {
  const sessionState = getSessionState();
  return {
    isModuleEnabled: (module: Module) => {
      return computed(() => {
        const { activeModules } = sessionState.generalSettings;
        return activeModules.includes(module);
      });
    }
  };
};

export const getPremium = () => {
  const sessionState = getSessionState();
  return computed(() => sessionState.premium);
};

export const currency = computed(() => {
  const sessionState = getSessionState();
  const { ticker_symbol } = sessionState.generalSettings.selectedCurrency;
  return ticker_symbol;
});

export const floatingPrecision = computed(() => {
  const sessionState = getSessionState();
  const { floatingPrecision } = sessionState.generalSettings;
  return floatingPrecision;
});
