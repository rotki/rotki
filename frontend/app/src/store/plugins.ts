import cloneDeep from 'lodash/cloneDeep';
import { PiniaPluginContext, StoreGeneric } from 'pinia';

export function StoreResetPlugin({ store }: PiniaPluginContext) {
  const initialState = cloneDeep(store.$state);
  store.$reset = () => {
    let state: any;
    if (store.$id === 'main') {
      state = cloneDeep(store.$state);
      state.newUser = false;
      state.connectionFailure = false;
    } else {
      state = cloneDeep(initialState);
    }
    store.$patch(toReactive(state));
  };
}

/**
 * Keeps track of the installed pinia stores.
 */
const storeMap = new Map<string, StoreGeneric>();

export function StoreTrackPlugin({ store }: PiniaPluginContext) {
  storeMap.set(store.$id, store);
}

/**
 * Resets the state of all the installed pinia stores.
 */
export const resetState = () => {
  for (const store of storeMap.values()) {
    store.$reset();
  }
};
