import { computed } from '@vue/composition-api';
import { SessionState } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { Module } from '@/types/modules';
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
  const { tickerSymbol } = sessionState.generalSettings.mainCurrency;
  return tickerSymbol;
});

export const floatingPrecision = computed(() => {
  const sessionState = getSessionState();
  const { uiFloatingPrecision } = sessionState.generalSettings;
  return uiFloatingPrecision;
});

export const dateDisplayFormat = computed(() => {
  const sessionState = getSessionState();
  const { dateDisplayFormat } = sessionState.generalSettings;
  return dateDisplayFormat;
});

export const tags = computed(() => {
  const sessionState = getSessionState();
  return sessionState.tags;
});
