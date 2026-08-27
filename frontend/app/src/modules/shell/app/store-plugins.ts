import type { PiniaPluginContext, StoreGeneric } from 'pinia';
import { cloneDeep } from 'es-toolkit';
import { logger } from '@/modules/core/common/logging/logging';

export function StoreResetPlugin({ store }: PiniaPluginContext): void {
  const initialState = cloneDeep(store.$state);
  store.$reset = (): void => {
    let state: any;
    if (store.$id === 'main') {
      state = cloneDeep(store.$state);
      state.connectionFailure = false;
    }
    else {
      state = cloneDeep(initialState);
    }
    store.$patch(toReactive(state));
    if (typeof store.reset === 'function')
      store.reset();
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
export function resetState(): void {
  for (const [name, store] of storeMap) {
    try {
      store.$reset();
    }
    catch (error: unknown) {
      logger.error(`error while clearing the ${name} store`, error);
    }
  }
}
