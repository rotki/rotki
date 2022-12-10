import cloneDeep from 'lodash/cloneDeep';
import { type PiniaPluginContext, type StoreGeneric } from 'pinia';

export function StoreResetPlugin({ store }: PiniaPluginContext): void {
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
  };
}

/**
 * Keeps track of the installed pinia stores.
 */
const storeMap = new Map<string, StoreGeneric>();

export function StoreTrackPlugin({ store }: PiniaPluginContext): void {
  storeMap.set(store.$id, store);
}

/**
 * Resets the state of all the installed pinia stores.
 */
export const resetState = (): void => {
  for (const store of storeMap.values()) {
    store.$reset();
  }
};
