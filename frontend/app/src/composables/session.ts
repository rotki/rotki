import { computed } from '@vue/composition-api';
import { SupportedCurrency } from '@/data/currencies';
import { SessionState } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { Currency } from '@/types/currency';
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

export const tags = computed(() => {
  const sessionState = getSessionState();
  return sessionState.tags;
});

export const setupGeneralSettings = () => {
  const sessionState = getSessionState();

  const currency = computed<Currency>(() => {
    return sessionState.generalSettings.mainCurrency;
  });

  const currencySymbol = computed<SupportedCurrency>(() => {
    return currency.value.tickerSymbol;
  });

  const floatingPrecision = computed<number>(() => {
    return sessionState.generalSettings.uiFloatingPrecision;
  });

  const dateDisplayFormat = computed<string>(() => {
    return sessionState.generalSettings.dateDisplayFormat;
  });

  return {
    currency,
    currencySymbol,
    floatingPrecision,
    dateDisplayFormat
  };
};

export const setupDisplayData = () => {
  const store = useStore();
  const sessionState = getSessionState();

  const shouldShowAmount = computed<boolean>(() => {
    return store.getters['session/shouldShowAmount'];
  });

  const shouldShowPercentage = computed<boolean>(() => {
    return store.getters['session/shouldShowPercentage'];
  });

  const scrambleData = computed<boolean>(() => {
    return sessionState.scrambleData;
  });

  return {
    shouldShowAmount,
    shouldShowPercentage,
    scrambleData
  };
};
