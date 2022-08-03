import { Nullable } from '@rotki/common';
import { computed } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { SupportedCurrency } from '@/data/currencies';
import { SyncAction } from '@/services/types-api';
import { Pinned, SessionState } from '@/store/session/types';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';
import { Currency } from '@/types/currency';
import { CreateAccountPayload, LoginCredentials } from '@/types/login';
import { Module } from '@/types/modules';
import { SettingsUpdate, Tag } from '@/types/user';
import { assert } from '@/utils/assertions';

export function getSessionState(): SessionState {
  const store = useStore();
  const sessionState = store.state.session;
  assert(sessionState);
  return sessionState;
}

export const useModules = () => {
  const sessionState = getSessionState();

  const activeModules = computed(
    () => sessionState.generalSettings.activeModules
  );

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

export const setupSession = () => {
  const store = useStore();
  const state = getSessionState();
  const syncConflict = computed(() => state.syncConflict);
  const username = computed(() => state.username);
  const privacyMode = computed(() => state.privacyMode);
  const animationsEnabled = computed(() => state.animationsEnabled);
  const lastBalanceSave = computed(() => state.lastBalanceSave);
  const lastDataUpload = computed(() => state.lastDataUpload);
  const nodeConnection = computed(() => state.nodeConnection);
  const pinned = computed(() => state.pinned);

  const login = (payload: LoginCredentials): Promise<ActionStatus> => {
    return store.dispatch('session/login', payload);
  };

  const logout = (): Promise<void> => {
    return store.dispatch('session/logout');
  };

  const createAccount = (
    payload: CreateAccountPayload
  ): Promise<ActionStatus> => {
    return store.dispatch('session/createAccount', payload);
  };

  const updateSettings = (update: SettingsUpdate): Promise<void> => {
    return store.dispatch('session/updateSettings', update);
  };

  const forceSync = (action: SyncAction): Promise<void> => {
    return store.dispatch('session/forceSync', action);
  };

  const changePrivacyMode = (privacyMode: number) => {
    store.commit('session/privacyMode', privacyMode);
  };

  const setAnimationsEnabled = (enabled: boolean) => {
    store.commit('session/setAnimationsEnabled', enabled);
  };

  const setPinned = (pinned: Nullable<Pinned>) => {
    store.commit('session/setPinned', pinned);
  };

  return {
    syncConflict,
    username,
    privacyMode,
    animationsEnabled,
    lastBalanceSave,
    lastDataUpload,
    nodeConnection,
    pinned,
    createAccount,
    login,
    logout,
    forceSync,
    updateSettings,
    changePrivacyMode,
    setAnimationsEnabled,
    setPinned
  };
};

export const getPremium = () => {
  const sessionState = getSessionState();
  return computed(() => sessionState.premium);
};

export const setPremium = (isPremium: boolean) => {
  const store = useStore();
  store.commit('session/premium', isPremium);
};

export const setupTags = () => {
  const store = useStore();
  const tags = computed<Tag[]>(() => {
    return store.getters['session/tags'];
  });

  const editTag = async (tag: Tag) => {
    return await store.dispatch('session/editTag', tag);
  };

  const addTag = async (tag: Tag) => {
    return await store.dispatch('session/addTag', tag);
  };

  const deleteTag = async (tagName: string) => {
    await store.dispatch('session/deleteTag', tagName);
  };

  return {
    tags,
    editTag,
    addTag,
    deleteTag
  };
};

export const setupGeneralSettings = () => {
  const sessionState = getSessionState();

  const currency = computed<Currency>(() => {
    return sessionState.generalSettings.mainCurrency;
  });

  const currencySymbol = computed<SupportedCurrency>(() => {
    return get(currency).tickerSymbol;
  });

  const floatingPrecision = computed<number>(() => {
    return sessionState.generalSettings.uiFloatingPrecision;
  });

  const dateDisplayFormat = computed<string>(() => {
    return sessionState.generalSettings.dateDisplayFormat;
  });

  const treatEth2AsEth = computed<boolean>(() => {
    return sessionState.generalSettings.treatEth2AsEth;
  });

  return {
    currency,
    currencySymbol,
    floatingPrecision,
    dateDisplayFormat,
    treatEth2AsEth
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

export const useDarkMode = () => {
  const store = useStore();
  const sessionState = getSessionState();
  const darkModeEnabled = computed(() => sessionState.darkModeEnabled);
  const updateDarkMode = (enabled: boolean) => {
    store.commit('session/setDarkModeEnabled', enabled);
  };
  return {
    darkModeEnabled,
    updateDarkMode
  };
};
