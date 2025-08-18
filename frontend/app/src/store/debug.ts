import type { PiniaPluginContext } from 'pinia';
import { BigNumber, bigNumberify } from '@rotki/common';
import { logger } from '@/utils/logging';

const PREFIX = 'pinia.store.';

function convert(data: any): any {
  if (Array.isArray(data))
    return data.map(entry => convert(entry));

  if (!isObject(data))
    return data;

  if (data instanceof BigNumber)
    return `bn::${data.toString()}`;

  if (data instanceof Set)
    return { __type: 'Set', values: Array.from(data).map(item => convert(item)) };

  if (data instanceof Map)
    return { __type: 'Map', entries: Array.from(data.entries()).map(([k, v]) => [convert(k), convert(v)]) };

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

  return JSON.parse(items, (_, value) => {
    if (typeof value === 'string' && value.startsWith('bn::'))
      return bigNumberify(value.replace('bn::', ''));

    if (isObject(value) && value.__type === 'Set')
      return new Set(value.values);

    if (isObject(value) && value.__type === 'Map')
      return new Map(value.entries);

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
