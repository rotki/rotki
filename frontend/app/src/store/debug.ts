import { BigNumber } from '@rotki/common';
import { PiniaPluginContext } from 'pinia';
import { bigNumberify } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

function convert(data: any): any {
  if (Array.isArray(data)) {
    return data.map(entry => convert(entry));
  }

  if (!isObject(data)) {
    return data;
  }

  if (data instanceof BigNumber) {
    return `bn::${data.toString()}`;
  }

  const converted: { [key: string]: any } = {};
  Object.keys(data).map(key => {
    const datum = data[key];
    converted[key] = convert(datum);
  });

  return converted;
}

const isObject = (data: any): boolean =>
  typeof data === 'object' &&
  data !== null &&
  !(data instanceof RegExp) &&
  !(data instanceof Error) &&
  !(data instanceof Date);

const storage = sessionStorage;

const getState = (key: string) => {
  const items = storage.getItem(key);
  if (!items) return null;

  return JSON.parse(items, (key1, value) => {
    if (typeof value === 'string' && value.startsWith('bn::')) {
      return bigNumberify(value.replace('bn::', ''));
    }
    return value;
  });
};

const setState = (key: string, state: any) => {
  storage.setItem(key, JSON.stringify(convert(state)));
};

function shouldPersistStore(): any {
  const debugSettings = window.interop?.debugSettings?.();
  const menuEnabled = debugSettings?.persistStore;
  const envEnabled = import.meta.env.VITE_PERSIST_STORE;
  const isTest = import.meta.env.VITE_TEST;
  return (menuEnabled || envEnabled) && !isTest;
}

export const storePiniaPlugins = (context: PiniaPluginContext) => {
  const persistStore = shouldPersistStore();

  const { store } = context;
  const storeId = store.$id;

  if (!persistStore) {
    storage.removeItem(storeId);
    return undefined;
  }

  try {
    const fromStorage = getState(storeId);
    if (fromStorage) {
      store.$patch(fromStorage);
    }
  } catch (e) {
    logger.error(e);
  }

  store.$subscribe(
    (_, state) => {
      try {
        setState(storeId, state);
      } catch (e) {
        logger.error(e);
      }
    },
    { detached: true }
  );
};
