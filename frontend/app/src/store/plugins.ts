import cloneDeep from 'lodash/cloneDeep';
import { type PiniaPluginContext, type StoreGeneric } from 'pinia';

export const StoreResetPlugin = ({ store }: PiniaPluginContext): void => {
  const initialState = cloneDeep(store.$state);
  store.$reset = (): void => {
    let state: any;
    if (store.$id === 'main') {
      state = cloneDeep(store.$state);
      state.newUser = false;
      state.connectionFailure = false;
    } else {
      state = cloneDeep(initialState);
    }
    store.$patch(toReactive(state));
    // If a store has its own reset function (e.g. to cancel actions)
    // Then we will also call this to properly cleanup.
    if (typeof store.reset === 'function') {
      store.reset();
    }
  };
};

/**
 * Keeps track of the installed pinia stores.
 */
const storeMap = new Map<string, StoreGeneric>();

export const StoreTrackPlugin = ({ store }: PiniaPluginContext): void => {
  storeMap.set(store.$id, store);
};

/**
 * Resets the state of all the installed pinia stores.
 */
export const resetState = (): void => {
  for (const store of storeMap.values()) {
    store.$reset();
  }
};
