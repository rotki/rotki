import type { PiniaPluginContext } from 'pinia';
import { logger } from '@/utils/logging';
import { BigNumber, bigNumberify } from '@rotki/common';

const PREFIX = 'pinia.store.';

function convert(data: any): any {
  if (Array.isArray(data))
    return data.map(entry => convert(entry));

  if (!isObject(data))
    return data;

  if (data instanceof BigNumber)
    return `bn::${data.toString()}`;

  const converted: Record<string, any> = {};
  Object.keys(data).map((key) => {
    const datum = data[key];
    converted[key] = convert(datum);
    return key;
  });

  return converted;
}

function isObject(data: any): boolean {
  return (
    typeof data === 'object'
    && data !== null
    && !(data instanceof RegExp)
    && !(data instanceof Error)
    && !(data instanceof Date)
  );
}

const storage = sessionStorage;

function getState(key: string): any {
  const items = storage.getItem(PREFIX + key);
  if (!items)
    return null;

  return JSON.parse(items, (key1, value) => {
    if (typeof value === 'string' && value.startsWith('bn::'))
      return bigNumberify(value.replace('bn::', ''));

    return value;
  });
}

function setState(key: string, state: any): void {
  storage.setItem(PREFIX + key, JSON.stringify(convert(state)));
}

function shouldPersistStore(): any {
  const debugSettings = window.interop?.debugSettings?.();
  const menuEnabled = debugSettings?.persistStore;
  const envEnabled = import.meta.env.VITE_PERSIST_STORE;
  const isTest = import.meta.env.VITE_TEST;
  return (menuEnabled || envEnabled) && !isTest;
}

export function StoreStatePersistsPlugin(context: PiniaPluginContext): void {
  const persistStore = shouldPersistStore();

  const { store } = context;
  const storeId = store.$id;

  if (!persistStore) {
    storage.removeItem(PREFIX + storeId);
    return undefined;
  }

  try {
    const fromStorage = getState(storeId);
    if (fromStorage) {
      // Ensures that components reload properly.
      if (storeId === 'session/premium') {
        fromStorage.componentsLoaded = false;
        fromStorage.componentsReady = false;
      }
      store.$patch(fromStorage);
    }
  }
  catch (error) {
    logger.error(error);
  }

  store.$subscribe((_, state) => {
    try {
      setState(storeId, state);
    }
    catch (error) {
      logger.error(error);
    }
  }, { detached: true });
}
